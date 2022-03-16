# Replaces Trigger Scope for Data Lake referances
## This can be improved to add further dynamic functionality (ie. read arm as JSON)

param
(
    [parameter(Mandatory = $false)] [String] $armTemplate,
    [parameter(Mandatory = $false)] [String] $globalParameters
)

$globalJson = (Get-Content -Path $globalParameters) | ConvertFrom-Json

$tempFilePath = "$($armTemplate).temp"
$find = $globalJson.DevDataLakeID.value
$replace = $globalJson.DataLakeID.value

(Get-Content -Path $armTemplate) -replace $find, $replace | Add-Content -Path $tempFilePath

Remove-Item -Path $armTemplate
Move-Item -Path $tempFilePath -Destination $armTemplate