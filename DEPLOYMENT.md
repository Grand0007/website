# Deployment Guide - AI Resume Updater Platform

This guide will help you deploy the AI Resume Updater platform to production.

## Prerequisites

- Node.js 18+ installed
- Azure account with Storage Account
- OpenAI API key
- Gmail account for OTP emails
- Domain name (optional, for production)

## Step 1: Local Development Setup

1. **Clone and Setup**
   ```bash
   git clone <your-repo-url>
   cd ai-resume-updater
   ./setup.sh
   ```

2. **Configure Environment Variables**
   ```bash
   cp .env.example .env
   # Edit .env with your actual values
   ```

3. **Test Locally**
   ```bash
   npm run dev
   ```

## Step 2: Azure Setup

### Create Azure Storage Account

1. Go to [Azure Portal](https://portal.azure.com)
2. Create a new Storage Account
3. Choose "StorageV2" account type
4. Select appropriate region
5. Configure networking (start with "Allow all networks")
6. Create the account

### Create Container

1. In your Storage Account, go to "Containers"
2. Create a new container named `resumes`
3. Set access level to "Private" for security
4. Note down the connection string

### Get Connection String

1. In Storage Account → Access keys
2. Copy the connection string
3. Add to your `.env` file

## Step 3: OpenAI Setup

1. Go to [OpenAI Platform](https://platform.openai.com)
2. Create an account and add billing
3. Generate an API key
4. Add to your `.env` file

## Step 4: Email Setup (Gmail)

### Enable 2-Factor Authentication
1. Go to Google Account settings
2. Enable 2-Factor Authentication

### Generate App Password
1. Go to Security → App passwords
2. Generate a new app password for "Mail"
3. Use this password in your `.env` file

## Step 5: Production Deployment

### Option A: Azure App Service

1. **Create App Service**
   ```bash
   # Install Azure CLI
   az login
   az group create --name myResourceGroup --location eastus
   az appservice plan create --name myAppServicePlan --resource-group myResourceGroup --sku B1
   az webapp create --name my-resume-app --resource-group myResourceGroup --plan myAppServicePlan
   ```

2. **Configure Environment Variables**
   ```bash
   az webapp config appsettings set --name my-resume-app --resource-group myResourceGroup --settings \
     JWT_SECRET="your-secret" \
     OPENAI_API_KEY="your-key" \
     AZURE_STORAGE_CONNECTION_STRING="your-connection-string" \
     EMAIL_USER="your-email" \
     EMAIL_PASSWORD="your-password"
   ```

3. **Deploy**
   ```bash
   npm run build
   az webapp deployment source config-zip --resource-group myResourceGroup --name my-resume-app --src dist.zip
   ```

### Option B: Docker Deployment

1. **Create Dockerfile**
   ```dockerfile
   FROM node:18-alpine
   WORKDIR /app
   COPY package*.json ./
   RUN npm ci --only=production
   COPY . .
   RUN npm run build
   EXPOSE 5000
   CMD ["npm", "start"]
   ```

2. **Build and Deploy**
   ```bash
   docker build -t ai-resume-updater .
   docker run -p 5000:5000 --env-file .env ai-resume-updater
   ```

### Option C: Vercel/Netlify (Frontend) + Railway/Render (Backend)

1. **Deploy Backend to Railway**
   - Connect your GitHub repo
   - Set environment variables
   - Deploy automatically

2. **Deploy Frontend to Vercel**
   - Connect your GitHub repo
   - Set build command: `cd client && npm run build`
   - Set output directory: `client/build`

## Step 6: Security Considerations

### Environment Variables
- Use strong, unique JWT secrets
- Never commit `.env` files to version control
- Use Azure Key Vault for production secrets

### CORS Configuration
- Update `CLIENT_URL` in production
- Restrict CORS origins to your domain

### Rate Limiting
- The app includes basic rate limiting
- Consider additional DDoS protection

### SSL/TLS
- Always use HTTPS in production
- Configure SSL certificates

## Step 7: Monitoring and Maintenance

### Logging
- Set up Azure Application Insights
- Monitor API usage and errors
- Track OpenAI API costs

### Backup
- Regular backups of Azure Storage
- Database backups if using Cosmos DB

### Updates
- Keep dependencies updated
- Monitor security advisories
- Regular security audits

## Troubleshooting

### Common Issues

1. **Email not sending**
   - Check Gmail app password
   - Verify 2FA is enabled
   - Check firewall settings

2. **Azure Storage errors**
   - Verify connection string
   - Check container permissions
   - Ensure container exists

3. **OpenAI API errors**
   - Check API key validity
   - Verify billing is set up
   - Check rate limits

4. **CORS errors**
   - Update CLIENT_URL in environment
   - Check browser console for details

### Performance Optimization

1. **File Upload**
   - Implement file compression
   - Add upload progress indicators
   - Consider CDN for file delivery

2. **AI Processing**
   - Implement request queuing
   - Add caching for similar requests
   - Monitor OpenAI usage

3. **Database**
   - Use connection pooling
   - Implement proper indexing
   - Consider read replicas

## Support

For issues and questions:
- Check the troubleshooting section
- Review Azure and OpenAI documentation
- Create an issue in the repository

## License

This project is licensed under the MIT License.