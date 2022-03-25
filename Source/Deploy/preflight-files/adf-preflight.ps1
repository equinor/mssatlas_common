param
(
    [parameter(Mandatory = $false)] [String] $ResourceGroupName,
    [parameter(Mandatory = $false)] [String] $DataFactoryName,
    [parameter(Mandatory = $false)] [String] $SubscriptionId
)
function triggerSortUtil {
    param([Microsoft.Azure.Commands.DataFactoryV2.Models.PSTrigger]$trigger,
    [Hashtable] $triggerNameResourceDict,
    [Hashtable] $visited,
    [System.Collections.Stack] $sortedList)
    if ($visited[$trigger.Name] -eq $true) {
        return;
    }
    $visited[$trigger.Name] = $true;
    if ($trigger.Properties.DependsOn) {
        $trigger.Properties.DependsOn | Where-Object {$_ -and $_.ReferenceTrigger} | ForEach-Object{
            triggerSortUtil -trigger $triggerNameResourceDict[$_.ReferenceTrigger.ReferenceName] -triggerNameResourceDict $triggerNameResourceDict -visited $visited -sortedList $sortedList
        }
    }
    $sortedList.Push($trigger)
}

function Get-SortedTriggers {
    param(
        [string] $DataFactoryName,
        [string] $ResourceGroupName
    )
    $triggers = Get-AzDataFactoryV2Trigger -ResourceGroupName $ResourceGroupName -DataFactoryName $DataFactoryName
    $triggerDict = @{}
    $visited = @{}
    $stack = new-object System.Collections.Stack
    $triggers | ForEach-Object{ $triggerDict[$_.Name] = $_ }
    $triggers | ForEach-Object{ triggerSortUtil -trigger $_ -triggerNameResourceDict $triggerDict -visited $visited -sortedList $stack }
    $sortedList = new-object Collections.Generic.List[Microsoft.Azure.Commands.DataFactoryV2.Models.PSTrigger]
    
    while ($stack.Count -gt 0) {
        $sortedList.Add($stack.Pop())
    }
    $sortedList
}


Write-Host "[$(Get-Date)] Pulling deployed triggers"
$triggersDeployed = Get-SortedTriggers -DataFactoryName $DataFactoryName -ResourceGroupName $ResourceGroupName

#Stop all triggers
Write-Host "[$(Get-Date)] Stopping deployed triggers"
$triggersDeployed | ForEach-Object -ThrottleLimit 30 -Parallel {
    if ($_.Properties.GetType().Name -eq "BlobEventsTrigger") {
        Write-Host "Skipping event trigger " $_.Name
    }elseif ($_.RuntimeState -eq "Started"){
        Write-Host "Stopping trigger" $_.Name
        Stop-AzDataFactoryV2Trigger -ResourceGroupName $using:ResourceGroupName -DataFactoryName $using:DataFactoryName -Name $_.Name -Force
    }
}

# Query running pipelines

$StartTime = Get-Date
$BeforeDate = $StartTime.AddDays(-30)
$MaxPollTime = $StartTime.AddMinutes(30)

$url = "https://management.azure.com/subscriptions/$($SubscriptionId)/resourceGroups/$($ResourceGroupName)/providers/Microsoft.DataFactory/factories/$($DataFactoryName)/queryPipelineRuns?api-version=2018-06-01"
$body = '{\"lastUpdatedAfter\":\"'+ $BeforeDate +'\",\"lastUpdatedBefore\":\"'+ $StartTime +'\",\"filters\":[{\"operand\":\"Status\",\"operator\":\"Equals\",\"values\":[\"InProgress\"]}]}'

Write-Host "[$(Get-Date)] Query for running pipelines"
Write-Host "[$(Get-Date)] API URL: " $url
Write-Host "[$(Get-Date)] Query" $body
$runningPipelines = $null

## Poll and wait until all jobs end
do {
    if($runningPipelines -ne $null) {
        Start-Sleep -s 15
    }
    Write-Host "[$(Get-Date)] Polled since $($StartTime). Current poll returns active pipelines:"
    $output = az rest --method post --url $url --body $body --headers "Content-Type=application/json"
    $runningPipelines = $output | ConvertFrom-Json
    $runningPipelines | ForEach-Object {
        Write-Host $_.pipeline
    }
    if((Get-Date) -gt $MaxPollTime) {
        ## TODO: add code to re-activate all triggers on failure
        Write-Error "Maxium time exceeded. Long running job not ending?"
    }
} while ($runningPipelines.value.count -ne 0)

$elapsedTime = $(Get-Date) - $StartTime

$totalTime = "{0:HH:mm:ss}" -f ([datetime]$elapsedTime.Ticks)
Write-Host "[$(Get-Date)] All pipelines are finished. Elapsed time $($totalTime). Ready to deploy." 

