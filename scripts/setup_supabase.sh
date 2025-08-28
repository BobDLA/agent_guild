#!/bin/bash

# Supabase Database Setup Script
# Usage: ./setup_supabase.sh <your-supabase-project-ref>

if [ -z "$1" ]; then
    echo "Usage: $0 <your-supabase-project-ref>"
    echo "Example: $0 abcdefghijklmnopqrstuvwxyz"
    exit 1
fi

PROJECT_REF="$1"
SUPABASE_URL="https://${PROJECT_REF}.supabase.co"

echo "Setting up database for project: $PROJECT_REF"
echo "Supabase URL: $SUPABASE_URL"
echo ""
echo "Please go to https://app.supabase.com/project/${PROJECT_REF}/sql/new"
echo "Copy the content from scripts/supabase_schema.sql and paste it there"
echo ""
echo "After running the SQL schema, you can import data with:"
echo "python scripts/export_to_supabase_rest.py"