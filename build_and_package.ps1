Remove-Item -Recurse -Force build -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force dist -ErrorAction SilentlyContinue

pyinstaller ProjectContextCopier-Windows.spec --clean

 = "ProjectContextCopier-v0.1.0-alpha"
 = "ProjectContextCopier-v0.1.0-alpha.zip"

if (Test-Path ) { Remove-Item -Recurse -Force  }
if (Test-Path ) { Remove-Item -Force  }

New-Item -ItemType Directory -Force -Path 

if (Test-Path "dist\ProjectContextCopier-Windows.exe") {
    Copy-Item "dist\ProjectContextCopier-Windows.exe" -Destination "\"
    Copy-Item "LICENSE" -Destination "\"
    Copy-Item "README.md" -Destination "\README.txt"
    Copy-Item "CHANGELOG.md" -Destination "\CHANGELOG.txt"
    
    Compress-Archive -Path  -DestinationPath 
    Remove-Item -Recurse -Force 
    
    Write-Output "Successfully rebuilt and packaged  with updated .exe and README."
} else {
    Write-Output "Build failed. executable not found in dist."
}
