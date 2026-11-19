param([string]$Doc, [string]$Pdf)
$w = New-Object -ComObject Word.Application
$w.Visible = $false
$w.DisplayAlerts = 0
try {
  $d = $w.Documents.Open($Doc, $false, $true)
  $d.ExportAsFixedFormat($Pdf, 17)
  "pages=" + $d.ComputeStatistics(2)
  $d.Close($false)
} finally { $w.Quit() }
