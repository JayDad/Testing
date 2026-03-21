"""
NAS 파일 전체 목록 스캔 & CSV/Excel 내보내기
- 메모리 절약: os.scandir + 스트리밍 CSV 기록 (파일 목록을 메모리에 쌓지 않음)
- 성능: 멀티스레드 병렬 디렉토리 스캔 (네트워크 I/O 병렬화)
- 대용량 대응: 설정한 행 수마다 파일을 분할 저장
- 출력: 폴더 depth, 파일 분류 태그, 폴더별 요약 시트 포함
"""

import os
import csv
import sys
import time
import argparse
import threading
from datetime import datetime
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue, Empty


# ── 설정 ──────────────────────────────────────────────
DEFAULT_NAS_PATH = r"\\NAS_IP\사업기획부"   # NAS 경로 (수정 필요)
OUTPUT_DIR = "."                             # 결과 파일 저장 위치
ROWS_PER_FILE = 500_000                      # 분할 기준 행 수 (50만 건)
FLUSH_INTERVAL = 1_000                       # 몇 건마다 디스크에 flush
SCAN_WORKERS = 8                             # 병렬 스캔 스레드 수
# ─────────────────────────────────────────────────────


# ── 파일 분류 매핑 ────────────────────────────────────
FILE_CATEGORIES = {
    "문서": {".doc", ".docx", ".hwp", ".hwpx", ".pdf", ".txt", ".rtf",
            ".odt", ".pages", ".tex", ".md"},
    "스프레드시트": {".xls", ".xlsx", ".xlsm", ".xlsb", ".csv", ".ods",
                  ".numbers", ".tsv"},
    "프레젠테이션": {".ppt", ".pptx", ".pps", ".ppsx", ".odp", ".key"},
    "이미지": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif",
              ".svg", ".webp", ".ico", ".psd", ".ai", ".eps", ".raw",
              ".cr2", ".nef", ".heic"},
    "영상": {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm",
            ".m4v", ".mpg", ".mpeg", ".3gp", ".ts"},
    "오디오": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a",
              ".opus", ".aiff"},
    "압축": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz",
            ".tgz", ".cab", ".iso"},
    "실행파일": {".exe", ".msi", ".bat", ".cmd", ".sh", ".app", ".dll",
               ".sys", ".com"},
    "코드": {".py", ".js", ".ts", ".java", ".c", ".cpp", ".h", ".cs",
            ".go", ".rs", ".rb", ".php", ".html", ".css", ".sql",
            ".json", ".xml", ".yaml", ".yml", ".ini", ".cfg", ".conf"},
    "데이터": {".db", ".sqlite", ".mdb", ".accdb", ".dbf", ".parquet",
              ".avro", ".hdf5", ".sav", ".dta"},
    "CAD/설계": {".dwg", ".dxf", ".step", ".stp", ".iges", ".stl",
                ".3ds", ".skp", ".blend"},
    "폰트": {".ttf", ".otf", ".woff", ".woff2", ".eot"},
}

# 역매핑: 확장자 → 카테고리 (빠른 조회용)
_EXT_TO_CATEGORY = {}
for cat, exts in FILE_CATEGORIES.items():
    for ext in exts:
        _EXT_TO_CATEGORY[ext] = cat


def get_category(ext: str) -> str:
    """확장자로 파일 카테고리 반환"""
    return _EXT_TO_CATEGORY.get(ext, "기타")


def format_size(size_bytes) -> str:
    """바이트를 읽기 쉬운 단위로 변환"""
    size_bytes = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(size_bytes) < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def get_depth(file_path: str, root_path: str) -> int:
    """루트 경로 기준 폴더 깊이 계산"""
    rel = os.path.relpath(os.path.dirname(file_path), root_path)
    if rel == ".":
        return 0
    return rel.count(os.sep) + 1


def get_depth_parts(file_path: str, root_path: str, max_depth: int = 5) -> list:
    """루트 기준 각 depth별 폴더명 리스트 반환"""
    rel = os.path.relpath(os.path.dirname(file_path), root_path)
    if rel == ".":
        return [""] * max_depth
    parts = rel.split(os.sep)
    # max_depth까지 채우고 부족하면 빈 문자열
    return [parts[i] if i < len(parts) else "" for i in range(max_depth)]


def safe_stat(entry: os.DirEntry):
    """파일 stat 정보를 안전하게 가져옴"""
    try:
        stat = entry.stat()
        return stat.st_size, stat.st_mtime, stat.st_ctime
    except (OSError, PermissionError):
        return 0, 0, 0


def scan_single_dir(dir_path: str):
    """
    단일 디렉토리를 스캔하여 (하위 디렉토리 목록, 파일 엔트리 목록) 반환.
    멀티스레드에서 병렬 호출됨.
    """
    subdirs = []
    files = []
    try:
        with os.scandir(dir_path) as it:
            for entry in it:
                try:
                    if entry.is_dir(follow_symlinks=False):
                        subdirs.append(entry.path)
                    elif entry.is_file(follow_symlinks=False):
                        size, mtime, ctime = safe_stat(entry)
                        _, ext = os.path.splitext(entry.name)
                        files.append((
                            entry.name,
                            ext.lower(),
                            entry.path,
                            os.path.dirname(entry.path),
                            size,
                            mtime,
                            ctime,
                        ))
                except (OSError, PermissionError) as e:
                    print(f"  [SKIP] {entry.path} → {e}", file=sys.stderr)
    except (OSError, PermissionError) as e:
        print(f"  [SKIP DIR] {dir_path} → {e}", file=sys.stderr)
    return subdirs, files


def parallel_scan(root_path: str, result_queue: Queue, workers: int = 8):
    """
    멀티스레드로 디렉토리를 병렬 탐색.
    결과는 result_queue에 파일 정보 튜플을 넣는다.
    완료 시 None을 넣어 종료 신호.
    """
    pending_dirs = Queue()
    pending_dirs.put(root_path)
    active_tasks = 0
    lock = threading.Lock()
    done_event = threading.Event()

    def process_dir(dir_path):
        nonlocal active_tasks
        subdirs, files = scan_single_dir(dir_path)

        # 파일 결과를 큐에 전달
        for f in files:
            result_queue.put(f)

        # 하위 디렉토리를 작업 큐에 추가
        with lock:
            for sd in subdirs:
                pending_dirs.put(sd)
                active_tasks += 1
            active_tasks -= 1  # 현재 작업 완료
            if active_tasks == 0 and pending_dirs.empty():
                done_event.set()

    with ThreadPoolExecutor(max_workers=workers) as executor:
        active_tasks = 1  # root

        while not done_event.is_set():
            try:
                dir_path = pending_dirs.get(timeout=0.5)
            except Empty:
                if done_event.is_set():
                    break
                continue

            with lock:
                if not done_event.is_set():
                    active_tasks += 1
            # 현재 디렉토리 수동 카운트 보정: process_dir 안에서 -1 하므로 여기서 +1 불필요
            # 사실 위에서 active_tasks +=1 하고 process_dir에서 -=1 하면 net 0
            # root 초기값=1 이고 process_dir에서 -=1 하므로 이후엔 subdirs 개수만큼 +=1
            with lock:
                active_tasks -= 1  # 보정: submit 자체는 작업이 아님

            executor.submit(process_dir, dir_path)

    result_queue.put(None)  # 종료 신호


def export_to_csv(nas_path: str, output_dir: str, rows_per_file: int, workers: int):
    """
    멀티스레드 스캔 + 스트리밍 CSV 기록.
    폴더별 통계도 수집.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fieldnames = [
        "파일명", "확장자", "분류", "경로", "폴더",
        "depth", "1depth", "2depth", "3depth", "4depth", "5depth",
        "크기(bytes)", "크기", "수정일", "생성일",
    ]

    file_index = 1
    row_count = 0
    total_count = 0
    total_size = 0
    csv_file = None
    writer = None
    output_files = []

    # 폴더별 요약 통계 수집
    folder_stats = defaultdict(lambda: {"파일수": 0, "총크기": 0, "확장자목록": set()})

    start_time = time.time()

    def open_new_file():
        nonlocal csv_file, writer, file_index, row_count
        if csv_file:
            csv_file.close()
        fname = os.path.join(
            output_dir,
            f"nas_filelist_{timestamp}_part{file_index:03d}.csv"
        )
        output_files.append(fname)
        csv_file = open(fname, "w", newline="", encoding="utf-8-sig")
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        row_count = 0
        file_index += 1
        return writer

    writer = open_new_file()

    print(f"\n{'='*60}")
    print(f" NAS 파일 목록 스캔 시작")
    print(f" 대상 경로 : {nas_path}")
    print(f" 스레드 수 : {workers}")
    print(f" 분할 기준 : {rows_per_file:,} 건/파일")
    print(f"{'='*60}\n")

    # 멀티스레드 스캔 시작
    result_queue = Queue(maxsize=10_000)
    scan_thread = threading.Thread(
        target=parallel_scan,
        args=(nas_path, result_queue, workers),
        daemon=True,
    )
    scan_thread.start()

    # 큐에서 결과를 꺼내며 CSV 기록
    while True:
        try:
            item = result_queue.get(timeout=5)
        except Empty:
            if not scan_thread.is_alive():
                break
            continue

        if item is None:
            break

        name, ext, path, folder, size, mtime, ctime = item

        depth = get_depth(path, nas_path)
        depth_parts = get_depth_parts(path, nas_path, 5)
        category = get_category(ext)

        row = {
            "파일명": name,
            "확장자": ext,
            "분류": category,
            "경로": path,
            "폴더": folder,
            "depth": depth,
            "1depth": depth_parts[0],
            "2depth": depth_parts[1],
            "3depth": depth_parts[2],
            "4depth": depth_parts[3],
            "5depth": depth_parts[4],
            "크기(bytes)": size,
            "크기": format_size(size),
            "수정일": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S") if mtime else "",
            "생성일": datetime.fromtimestamp(ctime).strftime("%Y-%m-%d %H:%M:%S") if ctime else "",
        }

        writer.writerow(row)
        row_count += 1
        total_count += 1
        total_size += size

        # 폴더별 통계 수집 (depth 1 기준)
        folder_key = depth_parts[0] if depth_parts[0] else "(루트)"
        stats = folder_stats[folder_key]
        stats["파일수"] += 1
        stats["총크기"] += size
        if ext:
            stats["확장자목록"].add(ext)

        if total_count % FLUSH_INTERVAL == 0:
            csv_file.flush()

        if total_count % 5_000 == 0:
            elapsed = time.time() - start_time
            rate = total_count / elapsed if elapsed > 0 else 0
            print(
                f"\r  스캔 중... {total_count:>10,} 건 | "
                f"{format_size(total_size):>10} | "
                f"{rate:,.0f} 건/초 | "
                f"파일 #{file_index - 1}",
                end="", flush=True,
            )

        if row_count >= rows_per_file:
            print(f"\n  → 파일 분할: {output_files[-1]} ({row_count:,} 건)")
            writer = open_new_file()

    if csv_file:
        csv_file.close()

    elapsed = time.time() - start_time

    # ── 폴더별 요약 CSV 저장 ──
    summary_path = os.path.join(output_dir, f"nas_folder_summary_{timestamp}.csv")
    summary_fields = ["폴더(1depth)", "파일수", "총크기(bytes)", "총크기", "주요확장자"]
    with open(summary_path, "w", newline="", encoding="utf-8-sig") as sf:
        sw = csv.DictWriter(sf, fieldnames=summary_fields)
        sw.writeheader()
        for folder_name in sorted(folder_stats.keys()):
            s = folder_stats[folder_name]
            top_exts = sorted(s["확장자목록"])[:10]
            sw.writerow({
                "폴더(1depth)": folder_name,
                "파일수": s["파일수"],
                "총크기(bytes)": s["총크기"],
                "총크기": format_size(s["총크기"]),
                "주요확장자": ", ".join(top_exts),
            })

    # ── 요약 리포트 ──
    print(f"\n\n{'='*60}")
    print(f" 스캔 완료!")
    print(f"{'='*60}")
    print(f"  총 파일 수 : {total_count:,} 건")
    print(f"  총 용량    : {format_size(total_size)}")
    print(f"  소요 시간  : {elapsed:.1f} 초")
    if elapsed > 0:
        print(f"  처리 속도  : {total_count / elapsed:,.0f} 건/초")
    print(f"  출력 파일  : {len(output_files)} 개")
    for f in output_files:
        fsize = os.path.getsize(f) if os.path.exists(f) else 0
        print(f"    - {f} ({format_size(fsize)})")
    print(f"  폴더 요약  : {summary_path}")
    print(f"{'='*60}\n")

    # ── 폴더별 요약 콘솔 출력 ──
    print(f"  {'폴더(1depth)':<30} {'파일수':>10} {'용량':>12}")
    print(f"  {'-'*30} {'-'*10} {'-'*12}")
    for folder_name in sorted(folder_stats.keys()):
        s = folder_stats[folder_name]
        print(f"  {folder_name:<30} {s['파일수']:>10,} {format_size(s['총크기']):>12}")
    print()

    return output_files, summary_path


def merge_to_excel(csv_files: list, summary_path: str, output_dir: str):
    """
    분할된 CSV + 요약을 하나의 Excel 파일로 병합.
    openpyxl 스트리밍 모드로 메모리 절약.
    """
    try:
        from openpyxl import Workbook
    except ImportError:
        print("\n  [INFO] openpyxl 미설치 → Excel 변환 생략")
        print("         pip install openpyxl 로 설치 후 재실행하세요.\n")
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    xlsx_path = os.path.join(output_dir, f"nas_filelist_{timestamp}.xlsx")

    wb = Workbook(write_only=True)

    # 시트1: 파일 목록
    ws1 = wb.create_sheet("파일목록")
    total = 0
    for csv_path in csv_files:
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            header = next(reader)
            if total == 0:
                ws1.append(header)
            for row in reader:
                ws1.append(row)
                total += 1

    # 시트2: 폴더별 요약
    ws2 = wb.create_sheet("폴더별요약")
    with open(summary_path, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        for row in reader:
            ws2.append(row)

    wb.save(xlsx_path)
    print(f"  Excel 저장 완료: {xlsx_path} ({total:,} 건, 2개 시트)")
    return xlsx_path


def main():
    parser = argparse.ArgumentParser(
        description="NAS 파일 전체 목록을 CSV로 내보내기 (멀티스레드, 메모리 효율적)"
    )
    parser.add_argument(
        "nas_path",
        nargs="?",
        default=DEFAULT_NAS_PATH,
        help=f"스캔할 NAS 경로 (기본: {DEFAULT_NAS_PATH})",
    )
    parser.add_argument(
        "-o", "--output",
        default=OUTPUT_DIR,
        help="결과 파일 저장 디렉토리",
    )
    parser.add_argument(
        "-r", "--rows",
        type=int,
        default=ROWS_PER_FILE,
        help=f"파일 분할 기준 행 수 (기본: {ROWS_PER_FILE:,})",
    )
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=SCAN_WORKERS,
        help=f"병렬 스캔 스레드 수 (기본: {SCAN_WORKERS})",
    )
    parser.add_argument(
        "--excel",
        action="store_true",
        help="CSV 완료 후 Excel(.xlsx)로 병합",
    )
    args = parser.parse_args()

    if not os.path.isdir(args.nas_path):
        print(f"\n  [ERROR] 경로를 찾을 수 없습니다: {args.nas_path}")
        print(f"          NAS가 마운트되어 있는지 확인하세요.\n")
        sys.exit(1)

    os.makedirs(args.output, exist_ok=True)

    csv_files, summary_path = export_to_csv(
        args.nas_path, args.output, args.rows, args.workers
    )

    if args.excel and csv_files:
        merge_to_excel(csv_files, summary_path, args.output)


if __name__ == "__main__":
    main()
