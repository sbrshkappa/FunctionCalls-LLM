#!/bin/bash

# ANSI color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to show a colorful progress bar
show_progress() {
    local current=$1
    local total=$2
    local width=50
    local percentage=$((current * 100 / total))
    local completed=$((width * current / total))
    
    printf "\r${YELLOW}[${NC}"
    for ((i=0; i<completed; i++)); do printf "${GREEN}█${NC}"; done
    for ((i=completed; i<width; i++)); do printf "${RED}▒${NC}"; done
    printf "${YELLOW}]${NC} ${CYAN}%3d%%${NC}" "$percentage"
}

# Deactivate virtual environment if it's active
deactivate 2>/dev/null

echo -e "${MAGENTA}🧹 Cleaning up global packages...${NC}"

# Count total packages for progress bar
total_packages=$(wc -l < requirements.txt)

# Uninstall packages from requirements.txt in global environment
current_package=0
while IFS= read -r package || [[ -n "$package" ]]; do
    package_name=$(echo "$package" | cut -d'=' -f1)
    echo -e "${BLUE}Uninstalling ${CYAN}$package_name${BLUE} globally...${NC}"
    pip uninstall -y "$package_name" > /dev/null 2>&1
    ((current_package++))
    show_progress $current_package $total_packages
done < requirements.txt

echo -e "\n\n${MAGENTA}🚀 Activating virtual environment and installing packages...${NC}"

# Activate virtual environment
source .venv/bin/activate

# Install packages from requirements.txt in virtual environment
pip install -r requirements.txt > /dev/null 2>&1

# Show a fake progress bar for installation (since we can't easily track pip install progress)
for i in {1..50}; do
    show_progress $i 50
    sleep 0.1
done

echo -e "\n\n${MAGENTA}📦 Packages installed in virtual environment:${NC}"
pip list

echo -e "${GREEN}✨ Process completed! Virtual environment is now active and packages are installed. ✨${NC}"