<#
  모핑 PPTX → MP4 (Windows PowerPoint 자동 내보내기)
  사내 PC 로컬 처리 — 외부 전송 없음

  사용:  powershell -ExecutionPolicy Bypass -File export_mp4.ps1 -Pptx deck.pptx [-Height 1080] [-Fps 30]
  또는:  export_mp4.bat 위로 PPTX 파일을 끌어다 놓기
  전제:  PowerPoint 2019 / Microsoft 365 (모핑 지원 버전)
#>
param(
  [Parameter(Mandatory = $true)][string]$Pptx,
  [string]$Out,
  [int]$Height = 1080,      # 720 / 1080 / 2160
  [int]$Fps = 30,
  [int]$DefaultSec = 3,     # 장면별 시간 미지정 슬라이드 기본값(초) — build.py 산출물은 hold 값이 이미 반영됨
  [int]$Quality = 100
)
$ErrorActionPreference = 'Stop'
$Pptx = (Resolve-Path $Pptx).Path
if (-not $Out) { $Out = [IO.Path]::ChangeExtension($Pptx, '.mp4') }

$app = New-Object -ComObject PowerPoint.Application
try {
  # Open(FileName, ReadOnly, Untitled, WithWindow)
  $pres = $app.Presentations.Open($Pptx, -1, 0, 0)
  # CreateVideo(FileName, UseTimingsAndNarrations, DefaultSlideDuration, VertResolution, FramesPerSecond, Quality)
  $pres.CreateVideo($Out, -1, $DefaultSec, $Height, $Fps, $Quality)
  Write-Host "렌더링 중 ... $Out"
  # CreateVideoStatus: 1 진행 · 2 대기 · 3 완료 · 4 실패
  while ($pres.CreateVideoStatus -in 1, 2) { Start-Sleep -Seconds 1 }
  if ($pres.CreateVideoStatus -eq 3) { Write-Host "완료: $Out" } else { throw "내보내기 실패 (status=$($pres.CreateVideoStatus))" }
  $pres.Close()
} finally {
  $app.Quit()
  [void][Runtime.InteropServices.Marshal]::ReleaseComObject($app)
}
