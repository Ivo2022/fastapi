#!/bin/sh

OUTPUT=$(cat /etc/*release)
echo "Detecting OS..."

if echo $OUTPUT | grep -q "Ubuntu"; then
    echo "Installing Python and Git for Ubuntu..."
    apt update -qq
    apt install -y python3 python3-venv python3-pip git
    SERVER_OS="Ubuntu"
elif echo $OUTPUT | grep -q "CentOS"; then
    echo "Installing Python and Git for CentOS..."
    yum install -y python3 python3-pip git
    SERVER_OS="CentOS"
else
    echo "Unsupported OS. Only Ubuntu and CentOS are supported."
    exit 1
fi

# Clone your system from GitHub
echo "Cloning your NGO database system..."
rm -rf ngo-system
git clone https://github.com/Ivo2022/fastapi.git ngo-system

cd ngo-system

# Create virtual environment and install requirements
echo "Setting up virtual environment..."
python3 -m venv venv
. venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Setup complete. You can now run the app with:"
echo "source venv/bin/activate && python main.py"

