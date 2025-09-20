#!/bin/bash
# Simple authentication script for E2E testing
# Accepts any username/password combination for testing purposes
# DO NOT USE IN PRODUCTION!

# Environment variables passed by Home Assistant:
# $username - The username entered by the user
# $password - The password entered by the user

# For E2E testing, we'll accept specific test credentials
if [ "$username" = "e2e_test" ] || [ "$username" = "test" ] || [ "$username" = "admin" ]; then
    # Print meta variables for user creation
    echo "name = E2E Test User"
    echo "group = system-admin"
    echo "local_only = true"
    exit 0
else
    # Reject other usernames
    exit 1
fi