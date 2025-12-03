# start.ps1
Clear-Host
Write-Host "Docker Development Manager" -ForegroundColor Cyan

while ($true) {
    Write-Host "`n----------------------------------------" -ForegroundColor Green
    Write-Host "CONTROL MENU" -ForegroundColor Green
    Write-Host "----------------------------------------"
    Write-Host "1. Start/Update environment (docker-compose up)"
    Write-Host "2. View live Output (Logs) [Ctrl+C to return]"
    Write-Host "3. Enter container terminal (Bash)"
    Write-Host "4. Run Unit Tests (pytest)"
    Write-Host "5. Stop containers (Stop)"
    Write-Host "6. Stop everything and Exit script"
    Write-Host "----------------------------------------"
    
    $selection = Read-Host "Select an option (1-6)"

    switch ($selection) {
        "1" {
            Write-Host "Starting containers..." -ForegroundColor Yellow
            # --build ensures that if requirements or Dockerfile change, it updates
            docker-compose up -d --build
            Write-Host "Done! Containers running." -ForegroundColor Green
        }
        "2" {
            Write-Host "Showing logs... (Press Ctrl+C to return to menu)" -ForegroundColor Yellow
            try {
                docker-compose logs -f api
            } catch {
                Write-Host "Error: Containers are likely not running." -ForegroundColor Red
            }
        }
        "3" {
            Write-Host "Connecting to terminal... (Type 'exit' to quit)" -ForegroundColor Yellow
            try {
                docker-compose exec api /bin/bash
            } catch {
                Write-Host "Error: Cannot connect. Ensure you use Option 1 first." -ForegroundColor Red
            }
        }
        "4" {
            Write-Host "Running Tests..." -ForegroundColor Cyan
            try {
                # Usamos 'run --rm' para crear un contenedor temporal solo para el test.
                # Funciona aunque no hayas dado a la Opción 1.
                docker-compose run --rm api pytest tests/
            } catch {
                Write-Host "Error running tests." -ForegroundColor Red
            }
        }
        "5" {
            Write-Host "Stopping containers..." -ForegroundColor Magenta
            docker-compose stop
            Write-Host "Containers stopped." -ForegroundColor Green
        }
        "6" {
            Write-Host "Shutting down and removing containers..." -ForegroundColor Red
            docker-compose down
            exit
        }
        Default {
            Write-Host "Invalid option." -ForegroundColor Red
        }
    }
}