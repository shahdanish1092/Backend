Set-StrictMode -Version Latest

# Ensure script runs from repository root
Set-Location -Path "C:\Users\danis\Office_automation"

Write-Output "Fetching origin..."
git fetch origin --prune

# Checkout or create main
if (git rev-parse --verify main 2>$null) {
    git checkout main
} else {
    git checkout -b main
}

Write-Output "Pulling latest main..."
try {
    git pull origin main
} catch {
    Write-Output "Pull failed or nothing to pull"
}

Write-Output "Merging update/hr-callback-n8n into main..."
$mergeOutput = git merge --no-edit update/hr-callback-n8n 2>&1
Write-Output "Merge command output:"
Write-Output $mergeOutput
if ($LASTEXITCODE -ne 0) {
    Write-Output "Merge conflict detected, aborting and retrying preferring branch changes"
    try {
        git merge --abort 2>$null
    } catch {
        Write-Output "Nothing to abort"
    }
    git merge -X theirs --no-edit update/hr-callback-n8n
} else {
    Write-Output "Merge completed cleanly"
}

Write-Output "Pushing main to origin..."
git push origin main

Write-Output "Done."
