# Quick Start Guide - AI Resume Updater

Get up and running with the AI Resume Updater platform in 5 minutes!

## 🚀 Quick Setup

### 1. Prerequisites
- Node.js 18+ installed
- Git installed

### 2. Clone and Setup
```bash
git clone <your-repo-url>
cd ai-resume-updater
./setup.sh
```

### 3. Configure Environment (Required)
Edit the `.env` file with your credentials:

```bash
# Generate a random JWT secret
JWT_SECRET=your-super-secret-jwt-key-change-this-in-production

# Your Gmail for OTP emails
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-gmail-app-password

# Azure Storage (create a free account)
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=your-account;AccountKey=your-key;EndpointSuffix=core.windows.net

# OpenAI API key (get from https://platform.openai.com)
OPENAI_API_KEY=your-openai-api-key
```

### 4. Start the Application
```bash
npm run dev
```

The application will be available at:
- Frontend: http://localhost:3000
- Backend: http://localhost:5000

## 🎯 First Steps

1. **Open the application** in your browser
2. **Sign up** with your email address
3. **Upload your resume** (PDF or DOCX)
4. **Paste a job description** and customize your resume
5. **Download** your AI-optimized resume

## 🔧 Required Services Setup

### Azure Storage (Free Tier Available)
1. Go to [Azure Portal](https://portal.azure.com)
2. Create a free Storage Account
3. Create a container named `resumes`
4. Copy the connection string to `.env`

### OpenAI API
1. Visit [OpenAI Platform](https://platform.openai.com)
2. Sign up and add billing (required)
3. Generate an API key
4. Add to `.env`

### Gmail Setup
1. Enable 2-Factor Authentication on your Google Account
2. Generate an App Password for "Mail"
3. Use the app password in `.env`

## 📱 Features Available

- ✅ **Email Authentication** - Secure OTP-based login
- ✅ **Resume Upload** - Support for PDF and DOCX files
- ✅ **AI Customization** - Tailor resumes to job descriptions
- ✅ **Skills Analysis** - Compare your skills with job requirements
- ✅ **Cover Letter Generation** - AI-powered cover letters
- ✅ **Cloud Storage** - Secure Azure-based file storage

## 🆘 Need Help?

- Check the [Deployment Guide](DEPLOYMENT.md) for detailed setup
- Review the [README](README.md) for feature documentation
- Common issues are covered in the troubleshooting section

## 🎉 You're Ready!

Your AI Resume Updater platform is now running! Start uploading resumes and customizing them for your dream job applications.