#!/bin/bash

SERVICE_NAME="smilefood_server.service"
SERVICE_FILE="./$SERVICE_NAME"
SYSTEMD_PATH="/etc/systemd/system/$SERVICE_NAME"

# Check if the script is running as root
if [ "$(id -u)" -ne 0 ]; then
    echo "$0 script must be run as root."
    echo "Try 'sudo bash $0'"
    exit 1
fi

# Check if the service file exists
if [ ! -f "$SERVICE_FILE" ]; then
    echo "Error: $SERVICE_FILE not found in the current directory."
    exit 1
fi

# Check if the systemd directory exists
sudo cp "$SERVICE_FILE" "$SYSTEMD_PATH"
if [ $? -ne 0 ]; then
    echo "Error: Failed to copy $SERVICE_FILE to $SYSTEMD_PATH."
    exit 1
fi
echo "Service file copied to $SYSTEMD_PATH."

# Set permissions for the service file
sudo chmod 644 "$SYSTEMD_PATH"
echo "Permissions set for $SYSTEMD_PATH."

# Reload systemd to recognize the new service
sudo systemctl daemon-reload
if [ $? -ne 0 ]; then
    echo "Error: Failed to reload systemd daemon."
    exit 1
fi
echo "Systemd daemon reloaded."

# Enable and start the service
sudo systemctl enable "$SERVICE_NAME"
if [ $? -ne 0 ]; then
    echo "Error: Failed to enable $SERVICE_NAME."
    exit 1
fi
echo "Service enabled."

# Start the service
sudo systemctl start "$SERVICE_NAME"
if [ $? -ne 0 ]; then
    echo "Error: Failed to start $SERVICE_NAME."
    exit 1
fi
echo "Service started successfully."

# Check the status of the service
sudo systemctl status "$SERVICE_NAME" --no-pager