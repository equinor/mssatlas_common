<#
.SYNOPSIS
v0.1 - Can be further improved with return

.DESCRIPTION
Finds all files in workspace. Adds to array with full path and name.

.PARAMETER path
Workspace folder path to start recursirve search from

.EXAMPLE
Invoke-WorkspacePathRead -path "/Shared"

.NOTES
General notes
#>

param
(
    [parameter(Mandatory = $true)] [String] $INPUT_FOLDER_NAME,
    [parameter(Mandatory = $true)] [String] $SOURCES_PATH
)

function Invoke-WorkspacePathRead {
    param (
        $path
    )
    Write-Debug "Invoke-RecursivePathRead $path" 
    $output = databricks workspace ls -l --absolute $path
    Write-Output "$path [Directory]"
    Write-Debug  ([array]$output | Out-String)

    foreach ($line in $output) {
        $fields = $line.Split("  ")
        Write-Debug "Process $fields[1]"
        if($fields[0] -eq "DIRECTORY"){
            Invoke-WorkspacePathRead -path $fields[1].Trim()
        }elseif ([string]::IsNullOrWhiteSpace($fields) -and $output.Count -eq 1){
            # Add this path
            $workspace_files.Add($path)
            Write-Output "$path is empty"
        }else{
            $workspace_files.Add($fields[1].Trim())
            Write-Output $fields[1].Trim()
        }
    }
}

<#
.SYNOPSIS
Short description

.DESCRIPTION
Long description

.PARAMETER WORKDIR_PATH2
Parameter description

.EXAMPLE
Invoke-RecursiveFolderRead -path "/Shared"

.NOTES
General notes
#>
function Invoke-RecursiveFolderRead {

    $items = Get-ChildItem "$SOURCES_PATH" -Recurse -File -Name 
    Write-Debug "Task: Create Databricks Directory Structure"
    foreach ($item in $items)  {
        $file = "/" + $INPUT_FOLDER_NAME + "/" + $item.Replace("\", "/")
        $file = $file.Substring(0, $file.LastIndexOf('.'))
        Write-Output $file
        $fs_files.Add($file.Trim())
    }
}

Write-Output "Artifact Files"
Write-Output "------------------------------------------------------"


$fs_files = New-Object System.Collections.Generic.List[string]
Invoke-RecursiveFolderRead

Write-Debug "Result array"
Write-Debug "------------------------------------------------------"
Write-Debug ([array]$fs_files | Out-String)
Write-Output "Files found: " $fs_files.Count

Write-Output "Workspace Files"
Write-Output "------------------------------------------------------"

$workspace_files = New-Object System.Collections.Generic.List[string]
Invoke-WorkspacePathRead

Write-Debug "Result array"
Write-Debug "------------------------------------------------------"
Write-Debug ([array]$workspace_files | Out-String)
Write-Output "Files found: " $workspace_files.Count

Write-Output "Delete files"
Write-Output "------------------------------------------------------"

$counter = 0
$workspace_files | ForEach-Object {
    if ($_ -notin $fs_files) {
        Write-Output $_
        databricks workspace rm $_
        $counter++
    }
}
Write-Output "Deleted $counter files and folders"