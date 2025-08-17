#!/bin/bash

echo "🚀 Setting up AI Resume Updater Platform"
echo "========================================"

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ first."
    exit 1
fi

# Check Node.js version
NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "❌ Node.js version 18+ is required. Current version: $(node -v)"
    exit 1
fi

echo "✅ Node.js version: $(node -v)"

# Install root dependencies
echo "📦 Installing root dependencies..."
npm install

# Install server dependencies
echo "📦 Installing server dependencies..."
cd server
npm install
cd ..

# Install client dependencies
echo "📦 Installing client dependencies..."
cd client
npm install
cd ..

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please update the .env file with your actual configuration values:"
    echo "   - JWT_SECRET: Generate a secure random string"
    echo "   - EMAIL_USER: Your Gmail address"
    echo "   - EMAIL_PASSWORD: Your Gmail app password"
    echo "   - AZURE_STORAGE_CONNECTION_STRING: Your Azure Storage connection string"
    echo "   - OPENAI_API_KEY: Your OpenAI API key"
else
    echo "✅ .env file already exists"
fi

# Create Azure container if needed
echo "🔧 Azure Setup Instructions:"
echo "   1. Create an Azure Storage Account"
echo "   2. Create a container named 'resumes'"
echo "   3. Get your connection string and add it to .env"
echo "   4. Ensure the container has public read access for resume downloads"

echo ""
echo "🎉 Setup complete!"
echo ""
echo "To start the application:"
echo "   npm run dev"
echo ""
echo "This will start both the server (port 5000) and client (port 3000)"
echo ""
echo "📚 Next steps:"
echo "   1. Update .env with your actual configuration"
echo "   2. Set up Azure Storage Account and container"
echo "   3. Get an OpenAI API key"
echo "   4. Configure Gmail for OTP emails"
echo "   5. Run 'npm run dev' to start the application"