# start.ps1
Clear-Host
Write-Host "Docker Development Manager" -ForegroundColor Cyan

while ($true) {
    Write-Host "`n----------------------------------------" -ForegroundColor Green
    Write-Host "CONTROL MENU" -ForegroundColor Green
    Write-Host "----------------------------------------"
    Write-Host "1. Start/Update environment (Normal mode)"
    Write-Host "2. Start/Update environment (Debug mode with debugpy)"
    Write-Host "3. View live Output (Logs) [Ctrl+C to return]"
    Write-Host "4. Enter container terminal (Bash)"
    Write-Host "5. Run Unit Tests (pytest)"
    Write-Host "6. Generate DB Migration (flask db migrate)"
    Write-Host "7. Run DB Migrations (flask db upgrade)"
    Write-Host "8. Stop containers (Stop)"
    Write-Host "9. Stop everything and Exit script"
    Write-Host "----------------------------------------"
    
    $selection = Read-Host "Select an option (1-9)"

    switch ($selection) {
        "1" {
            Write-Host "Starting containers in NORMAL MODE..." -ForegroundColor Yellow
            Write-Host "Container name: bitsXLaMarato_api_dev" -ForegroundColor Cyan
            Write-Host "Port: 5000" -ForegroundColor Cyan
            # --build ensures that if requirements or Dockerfile change, it updates
            docker-compose -f docker-compose.yml up -d --build
            Write-Host "Done! Containers running in normal mode." -ForegroundColor Green
        }
        "2" {
            Write-Host "Starting containers in DEBUG MODE..." -ForegroundColor Yellow
            Write-Host "Container name: bitsXLaMarato_api_debug" -ForegroundColor Cyan
            Write-Host "API Port: 5000 | Debug Port: 5678" -ForegroundColor Cyan
            Write-Host "Use: Run & Debug (Ctrl+Shift+D) -> 'Python Debugger: Flask (Docker Remote)' -> F5" -ForegroundColor Magenta
            # --build ensures that if requirements or Dockerfile change, it updates
            docker-compose -f docker-compose.debug.yml up -d --build
            Write-Host "Done! Containers running in debug mode. Waiting for debugger connection..." -ForegroundColor Green
            Start-Sleep -Seconds 2
            Write-Host "Opening logs to show debugger status..." -ForegroundColor Yellow
            docker-compose -f docker-compose.debug.yml logs -f api
        }
        "3" {
            Write-Host "Showing logs... (Press Ctrl+C to return to menu)" -ForegroundColor Yellow
            Write-Host "Detecting active mode..." -ForegroundColor Cyan
            $normalRunning = docker ps -q -f "name=bitsXLaMarato_api_dev" 2>$null
            $debugRunning = docker ps -q -f "name=bitsXLaMarato_api_debug" 2>$null
            
            if ($debugRunning) {
                Write-Host "Debug mode container detected" -ForegroundColor Magenta
                docker-compose -f docker-compose.debug.yml logs -f api
            } elseif ($normalRunning) {
                Write-Host "Normal mode container detected" -ForegroundColor Green
                docker-compose -f docker-compose.yml logs -f api
            } else {
                Write-Host "No containers running." -ForegroundColor Red
            }
        }
        "4" {
            Write-Host "Connecting to terminal... (Type 'exit' to quit)" -ForegroundColor Yellow
            Write-Host "Detecting active mode..." -ForegroundColor Cyan
            $normalRunning = docker ps -q -f "name=bitsXLaMarato_api_dev" 2>$null
            $debugRunning = docker ps -q -f "name=bitsXLaMarato_api_debug" 2>$null
            
            try {
                if ($debugRunning) {
                    Write-Host "Connecting to debug mode container..." -ForegroundColor Magenta
                    docker-compose -f docker-compose.debug.yml exec api /bin/bash
                } elseif ($normalRunning) {
                    Write-Host "Connecting to normal mode container..." -ForegroundColor Green
                    docker-compose -f docker-compose.yml exec api /bin/bash
                } else {
                    Write-Host "Error: No containers running. Start with option 1 or 2 first." -ForegroundColor Red
                }
            } catch {
                Write-Host "Error: Cannot connect to container." -ForegroundColor Red
            }
        }
        "5" {
            Write-Host "Running Tests..." -ForegroundColor Cyan
            try {
                # Usamos 'run --rm' para crear un contenedor temporal solo para el test.
                # Funciona aunque no hayas dado a la Opción 1.
                docker-compose -f docker-compose.yml run --rm api pytest tests/
            } catch {
                Write-Host "Error running tests." -ForegroundColor Red
            }
        }
        "6" {
            Write-Host "Generating new migration version..." -ForegroundColor Cyan
            $migrationMessage = Read-Host "Introduce migration message:"
            if ([string]::IsNullOrWhiteSpace($migrationMessage)) {
                $migrationMessage = "auto-generated migration"
            }
            $composeFile = "docker-compose.yml"
            $normalRunning = docker ps -q -f "name=bitsXLaMarato_api_dev" 2>$null
            $debugRunning = docker ps -q -f "name=bitsXLaMarato_api_debug" 2>$null
            if ($debugRunning) {
                $composeFile = "docker-compose.debug.yml"
                Write-Host "Debug mode detected. Building migration via debug stack..." -ForegroundColor Magenta
            } elseif ($normalRunning) {
                Write-Host "Normal mode detected. Building migration via dev stack..." -ForegroundColor Green
            } else {
                Write-Host "No running containers detected. Using standard compose file." -ForegroundColor Yellow
            }
            try {
                docker-compose -f $composeFile run --rm api flask db migrate -m "$migrationMessage"
                Write-Host "Migration created successfully." -ForegroundColor Green
            } catch {
                Write-Host "Error generating migration." -ForegroundColor Red
            }
        }
        "7" {
            Write-Host "Running database migrations..." -ForegroundColor Cyan
            $composeFile = "docker-compose.yml"
            $normalRunning = docker ps -q -f "name=bitsXLaMarato_api_dev" 2>$null
            $debugRunning = docker ps -q -f "name=bitsXLaMarato_api_debug" 2>$null
            if ($debugRunning) {
                $composeFile = "docker-compose.debug.yml"
                Write-Host "Debug mode detected. Applying migrations via debug stack..." -ForegroundColor Magenta
            } elseif ($normalRunning) {
                Write-Host "Normal mode detected. Applying migrations via dev stack..." -ForegroundColor Green
            } else {
                Write-Host "No running containers detected. Using standard compose file." -ForegroundColor Yellow
            }
            try {
                docker-compose -f $composeFile run --rm api flask db upgrade
                Write-Host "Migrations executed successfully." -ForegroundColor Green
            } catch {
                Write-Host "Error running migrations." -ForegroundColor Red
            }
        }
        "8" {
            Write-Host "Stopping containers..." -ForegroundColor Magenta
            Write-Host "Detecting running containers..." -ForegroundColor Cyan
            $normalRunning = docker ps -q -f "name=bitsXLaMarato_api_dev" 2>$null
            $debugRunning = docker ps -q -f "name=bitsXLaMarato_api_debug" 2>$null
            
            if ($debugRunning) {
                Write-Host "Stopping debug mode container..." -ForegroundColor Magenta
                docker-compose -f docker-compose.debug.yml stop
            }
            if ($normalRunning) {
                Write-Host "Stopping normal mode container..." -ForegroundColor Green
                docker-compose -f docker-compose.yml stop
            }
            if (-not $normalRunning -and -not $debugRunning) {
                Write-Host "No containers running." -ForegroundColor Yellow
            } else {
                Write-Host "Containers stopped." -ForegroundColor Green
            }
        }
        "9" {
            Write-Host "Shutting down and removing containers..." -ForegroundColor Red
            Write-Host "Detecting running containers..." -ForegroundColor Cyan
            $normalRunning = docker ps -q -f "name=bitsXLaMarato_api_dev" 2>$null
            $debugRunning = docker ps -q -f "name=bitsXLaMarato_api_debug" 2>$null
            
            if ($debugRunning) {
                Write-Host "Removing debug mode container..." -ForegroundColor Magenta
                docker-compose -f docker-compose.debug.yml down
            }
            if ($normalRunning) {
                Write-Host "Removing normal mode container..." -ForegroundColor Green
                docker-compose -f docker-compose.yml down
            }
            Write-Host "All containers removed. Exiting..." -ForegroundColor Red
            exit
        }
        Default {
            Write-Host "Invalid option." -ForegroundColor Red
        }
    }
}
