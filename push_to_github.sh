#!/bin/bash

echo "🚀 Pushing Dungeon Odyssey Pipeline to GitHub..."
echo "=================================================="

# Initialize git
git init

# Add all files
git add -A

# Commit
git commit -m "Initial commit: Dungeon Odyssey Production Pipeline v4.1 with Tier 1 & Tier 2 upgrades"

# Add remote
git remote add origin https://github.com/Vishal9829/dungeon-odyssey-production-pipeline.git

# Push
git branch -M main
git push -u origin main

echo "✅ Successfully pushed to GitHub!"
echo "Repository: https://github.com/Vishal9829/dungeon-odyssey-production-pipeline"