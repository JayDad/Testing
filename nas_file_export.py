"""
NAS 파일 전체 목록 스캔 & CSV/Excel 내보내기
- 메모리 절약: os.scandir + 스트리밍 CSV 기록 (파일 목록을 메모리에 쌓지 않음)
- 대용량 대응: 설정한 행 수마다 파일을 분할 저장
- 진행 표시: 스캔 중 실시간 카운트 출력
"""

import os
import csv
import sys
import time
import argparse
from datetime import datetime
from pathlib import Path


# ── 설정 ──────────────────────────────────────────────
DEFAULT_NAS_PATH = r"\\NAS_IP\사업기획부"   # NAS 경로 (수정 필요)
OUTPUT_DIR = "."                             # 결과 파일 저장 위치
ROWS_PER_FILE = 500_000                      # 분할 기준 행 수 (50만 건)
FLUSH_INTERVAL = 1_000                       # 몇 건마다 디스크에 flush
# ─────────────────────────────────────────────────────


def format_size(size_bytes: int) -> str:
    """바이트를 읽기 쉬운 단위로 변환"""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(size_bytes) < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def safe_stat(entry: os.DirEntry):
    """파일 stat 정보를 안전하게 가져옴 (권한 에러 등 방어)"""
    try:
        stat = entry.stat()
        return stat.st_size, stat.st_mtime, stat.st_ctime
    except (OSError, PermissionError):
        return 0, 0, 0


def scan_directory(root_path: str):
    """
    제너레이터: 디렉토리를 재귀 탐색하며 파일 정보를 하나씩 yield.
    메모리에 전체 목록을 쌓지 않는다.
    """
    stack = [root_path]

    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as it:
                for entry in it:
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(entry.path)
                        elif entry.is_file(follow_symlinks=False):
                            size, mtime, ctime = safe_stat(entry)
                            _, ext = os.path.splitext(entry.name)
                            yield {
                                "파일명": entry.name,
                                "확장자": ext.lower(),
                                "경로": entry.path,
                                "폴더": os.path.dirname(entry.path),
                                "크기(bytes)": size,
                                "크기": format_size(size),
                                "수정일": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S") if mtime else "",
                                "생성일": datetime.fromtimestamp(ctime).strftime("%Y-%m-%d %H:%M:%S") if ctime else "",
                            }
                    except (OSError, PermissionError) as e:
                        print(f"  [SKIP] {entry.path} → {e}", file=sys.stderr)
        except (OSError, PermissionError) as e:
            print(f"  [SKIP DIR] {current} → {e}", file=sys.stderr)


def export_to_csv(nas_path: str, output_dir: str, rows_per_file: int):
    """
    스트리밍 방식으로 CSV 파일에 기록.
    rows_per_file 건마다 새 파일로 분할.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fieldnames = ["파일명", "확장자", "경로", "폴더", "크기(bytes)", "크기", "수정일", "생성일"]

    file_index = 1
    row_count = 0
    total_count = 0
    total_size = 0
    error_count = 0
    csv_file = None
    writer = None
    output_files = []

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
        csv_file = open(fname, "w", newline="", encoding="utf-8-sig")  # utf-8-sig: Excel 한글 호환
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        row_count = 0
        file_index += 1
        return writer

    writer = open_new_file()

    print(f"\n{'='*60}")
    print(f" NAS 파일 목록 스캔 시작")
    print(f" 대상 경로: {nas_path}")
    print(f" 분할 기준: {rows_per_file:,} 건/파일")
    print(f"{'='*60}\n")

    for file_info in scan_directory(nas_path):
        writer.writerow(file_info)
        row_count += 1
        total_count += 1
        total_size += file_info["크기(bytes)"]

        # 주기적 flush → 크래시 시에도 데이터 보존
        if total_count % FLUSH_INTERVAL == 0:
            csv_file.flush()

        # 진행 상황 출력 (터미널 한 줄 덮어쓰기)
        if total_count % 5_000 == 0:
            elapsed = time.time() - start_time
            rate = total_count / elapsed if elapsed > 0 else 0
            print(
                f"\r  스캔 중... {total_count:>10,} 건 | "
                f"{format_size(total_size):>10} | "
                f"{rate:,.0f} 건/초 | "
                f"파일 #{file_index - 1}",
                end="", flush=True
            )

        # 분할 기준 도달 시 새 파일
        if row_count >= rows_per_file:
            print(f"\n  → 파일 분할: {output_files[-1]} ({row_count:,} 건)")
            writer = open_new_file()

    if csv_file:
        csv_file.close()

    elapsed = time.time() - start_time

    # ── 요약 리포트 ──
    print(f"\n\n{'='*60}")
    print(f" 스캔 완료!")
    print(f"{'='*60}")
    print(f"  총 파일 수 : {total_count:,} 건")
    print(f"  총 용량    : {format_size(total_size)}")
    print(f"  소요 시간  : {elapsed:.1f} 초")
    print(f"  출력 파일  : {len(output_files)} 개")
    for f in output_files:
        fsize = os.path.getsize(f) if os.path.exists(f) else 0
        print(f"    - {f} ({format_size(fsize)})")
    print(f"{'='*60}\n")

    return output_files


def merge_to_excel(csv_files: list, output_dir: str):
    """
    (선택) 분할된 CSV를 하나의 Excel 파일로 병합.
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

    wb = Workbook(write_only=True)  # 스트리밍 모드: 메모리 최소화
    ws = wb.create_sheet("파일목록")

    total = 0
    for csv_path in csv_files:
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            header = next(reader)
            if total == 0:
                ws.append(header)
            for row in reader:
                ws.append(row)
                total += 1

    wb.save(xlsx_path)
    print(f"  Excel 저장 완료: {xlsx_path} ({total:,} 건)")
    return xlsx_path


def main():
    parser = argparse.ArgumentParser(
        description="NAS 파일 전체 목록을 CSV로 내보내기 (메모리 효율적)"
    )
    parser.add_argument(
        "nas_path",
        nargs="?",
        default=DEFAULT_NAS_PATH,
        help=f"스캔할 NAS 경로 (기본: {DEFAULT_NAS_PATH})"
    )
    parser.add_argument(
        "-o", "--output",
        default=OUTPUT_DIR,
        help="결과 파일 저장 디렉토리"
    )
    parser.add_argument(
        "-r", "--rows",
        type=int,
        default=ROWS_PER_FILE,
        help=f"파일 분할 기준 행 수 (기본: {ROWS_PER_FILE:,})"
    )
    parser.add_argument(
        "--excel",
        action="store_true",
        help="CSV 완료 후 Excel(.xlsx)로 병합"
    )
    args = parser.parse_args()

    # 경로 검증
    if not os.path.isdir(args.nas_path):
        print(f"\n  [ERROR] 경로를 찾을 수 없습니다: {args.nas_path}")
        print(f"          NAS가 마운트되어 있는지 확인하세요.\n")
        sys.exit(1)

    os.makedirs(args.output, exist_ok=True)

    # CSV 내보내기
    csv_files = export_to_csv(args.nas_path, args.output, args.rows)

    # Excel 변환 (선택)
    if args.excel and csv_files:
        merge_to_excel(csv_files, args.output)


if __name__ == "__main__":
    main()
