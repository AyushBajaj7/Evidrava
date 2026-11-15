<#
Recalculate temporary .xlsx scenario files with a private Microsoft Excel
automation instance. This adapter accepts the LibreOffice-style arguments
emitted by the received workbook regression runner:

  --headless --convert-to xlsx --outdir <directory> <input.xlsx>...

It never opens a browser, follows workbook links, enables macros, or writes to
the input files. Each recalculated workbook is saved under the supplied output
directory with the same filename.
#>
[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Arguments
)

$ErrorActionPreference = 'Stop'

function Get-ExcelArguments {
    param([string[]]$Values)

    $outdir = $null
    $inputs = [System.Collections.Generic.List[string]]::new()
    for ($index = 0; $index -lt $Values.Count; $index++) {
        $value = $Values[$index]
        if ($value -eq '--outdir') {
            if ($index + 1 -ge $Values.Count) { throw 'Missing value after --outdir.' }
            $index++
            $outdir = $Values[$index]
            continue
        }
        if ($value -in @('--headless', '--convert-to', 'xlsx')) { continue }
        if ($value -like '*.xlsx') { $inputs.Add($value) }
    }
    if (-not $outdir) { throw 'The temporary output directory was not supplied.' }
    if ($inputs.Count -eq 0) { throw 'No temporary .xlsx inputs were supplied.' }
    [pscustomobject]@{ Outdir = $outdir; Inputs = $inputs }
}

$parsed = Get-ExcelArguments -Values $Arguments
$outdir = [System.IO.Path]::GetFullPath($parsed.Outdir)
if (-not (Test-Path -LiteralPath $outdir)) {
    New-Item -ItemType Directory -Path $outdir -Force | Out-Null
}

$excel = $null
try {
    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $excel.DisplayAlerts = $false
    $excel.ScreenUpdating = $false
    $excel.EnableEvents = $false
    $excel.AskToUpdateLinks = $false
    # msoAutomationSecurityForceDisable. Test workbooks are .xlsx, but this
    # removes any possibility of a macro executing if an input is replaced.
    try { $excel.AutomationSecurity = 3 } catch { }
    $excel.Calculation = -4105 # xlCalculationAutomatic
    $excel.CalculateBeforeSave = $true

    foreach ($input in $parsed.Inputs) {
        $inputPath = [System.IO.Path]::GetFullPath($input)
        if (-not (Test-Path -LiteralPath $inputPath -PathType Leaf)) {
            throw "Temporary scenario workbook was not found: $inputPath"
        }
        $outputPath = Join-Path $outdir ([System.IO.Path]::GetFileName($inputPath))
        if (Test-Path -LiteralPath $outputPath) {
            throw "Refusing to overwrite an existing calculated scenario: $outputPath"
        }
        $book = $null
        try {
            # UpdateLinks=0 and ReadOnly=$true protect the source scenario.
            $book = $excel.Workbooks.Open($inputPath, 0, $true)
            $excel.CalculateFullRebuild()
            # 51 is xlOpenXMLWorkbook (.xlsx).
            $book.SaveAs($outputPath, 51)
            Write-Output ("Recalculated: " + [System.IO.Path]::GetFileName($inputPath))
        }
        finally {
            if ($null -ne $book) {
                $book.Close($false)
                [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($book)
            }
        }
    }
}
finally {
    if ($null -ne $excel) {
        $excel.Quit()
        [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($excel)
    }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
