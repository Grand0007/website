# AI Resume Updater

An AI-powered resume customization platform that automatically updates resumes to match job descriptions, enhancing job seekers' competitiveness in the market.

## 🚀 Features

### MVP Features
- **AI Resume Customization**: Automatically updates uploaded resumes based on job descriptions
- **Email-based Authentication**: Secure OTP (One-Time Password) login system
- **Resume Upload & Parsing**: Support for PDF and DOCX resume files
- **Job Matching Analysis**: AI-powered analysis of resume-job compatibility
- **Azure Cloud Integration**: Scalable cloud infrastructure for file storage and processing

### Advanced Features
- **Multiple Customization Levels**: Light, moderate, and heavy resume modifications
- **Skill Gap Analysis**: Identifies missing skills and provides improvement suggestions
- **Batch Resume Analysis**: Compare multiple resumes against job descriptions
- **Processing History**: Track all AI customizations and analyses
- **User Dashboard**: Comprehensive overview of resumes and statistics

## 🏗️ Architecture

### Backend (FastAPI + Python)
- **FastAPI**: Modern, fast web framework for building APIs
- **Azure Services**: Cloud storage, Cosmos DB, and Key Vault integration
- **AI Integration**: OpenAI GPT-4 for resume analysis and customization
- **Authentication**: JWT tokens with OTP email verification
- **File Processing**: PDF and DOCX parsing with structured data extraction

### Frontend (React + Material-UI)
- **React 18**: Modern React with hooks and context
- **Material-UI**: Professional, responsive UI components
- **React Query**: Efficient data fetching and caching
- **React Router**: Client-side routing
- **Responsive Design**: Mobile-first approach with modern UX

### Database & Storage
- **PostgreSQL**: Primary database for user and resume data
- **Azure Blob Storage**: File storage for uploaded resumes
- **Azure Cosmos DB**: Optional NoSQL database for processing logs
- **Redis**: Caching and session management

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- Azure account (optional, for cloud features)
- OpenAI API key

### Environment Variables

Create `.env` file in the root directory:

```env
# Email Configuration
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
FROM_EMAIL=your_email@gmail.com

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# Azure Configuration (Optional)
AZURE_STORAGE_CONNECTION_STRING=your_azure_storage_connection
AZURE_COSMOS_ENDPOINT=your_cosmos_endpoint
AZURE_COSMOS_KEY=your_cosmos_key
AZURE_KEY_VAULT_URL=your_key_vault_url
```

### Quick Start with Docker

1. **Clone the repository**
```bash
git clone <repository-url>
cd ai-resume-updater
```

2. **Start all services**
```bash
docker-compose up -d
```

3. **Access the application**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/api/docs

### Manual Setup

#### Backend Setup

1. **Navigate to backend directory**
```bash
cd backend
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Download spaCy model**
```bash
python -m spacy download en_core_web_sm
```

5. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

6. **Run the application**
```bash
uvicorn main:app --reload
```

#### Frontend Setup

1. **Navigate to frontend directory**
```bash
cd frontend
```

2. **Install dependencies**
```bash
npm install
```

3. **Start development server**
```bash
npm start
```

## 📚 API Documentation

### Authentication Endpoints
- `POST /api/auth/request-otp` - Request OTP for email
- `POST /api/auth/verify-otp` - Verify OTP and login
- `GET /api/auth/me` - Get current user info
- `POST /api/auth/logout` - Logout user

### Resume Management
- `POST /api/resume/upload` - Upload resume file
- `GET /api/resume/` - Get user's resumes
- `GET /api/resume/{id}` - Get specific resume
- `PUT /api/resume/{id}` - Update resume
- `DELETE /api/resume/{id}` - Delete resume

### AI Processing
- `POST /api/ai/analyze-match` - Analyze resume-job match
- `POST /api/ai/customize-resume` - AI customize resume
- `POST /api/ai/batch-analyze` - Batch analyze resumes
- `GET /api/ai/suggestions/{id}` - Get improvement suggestions

### User Management
- `GET /api/user/profile` - Get user profile
- `PUT /api/user/profile` - Update profile
- `GET /api/user/stats` - Get user statistics
- `DELETE /api/user/account` - Delete account

## 🔧 Configuration

### Database Configuration
The application supports PostgreSQL for production and SQLite for development:

```python
# For PostgreSQL
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# For SQLite (development)
DATABASE_URL=sqlite:///./ai_resume.db
```

### Azure Services Configuration
Configure Azure services for cloud deployment:

1. **Azure Blob Storage**: For resume file storage
2. **Azure Cosmos DB**: For processing logs and analytics
3. **Azure Key Vault**: For secure secret management

### Email Configuration
Set up email service for OTP delivery:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
```

## 🚀 Deployment

### Azure App Service Deployment

1. **Create Azure resources**
```bash
# Create resource group
az group create --name ai-resume-rg --location eastus

# Create App Service plan
az appservice plan create --name ai-resume-plan --resource-group ai-resume-rg --sku B1 --is-linux

# Create web apps
az webapp create --name ai-resume-api --resource-group ai-resume-rg --plan ai-resume-plan --runtime "PYTHON|3.11"
az webapp create --name ai-resume-app --resource-group ai-resume-rg --plan ai-resume-plan --runtime "NODE|18-lts"
```

2. **Deploy backend**
```bash
cd backend
az webapp up --name ai-resume-api --resource-group ai-resume-rg
```

3. **Deploy frontend**
```bash
cd frontend
npm run build
az webapp up --name ai-resume-app --resource-group ai-resume-rg
```

### Docker Deployment

```bash
# Build and deploy with Docker Compose
docker-compose -f docker-compose.prod.yml up -d
```

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest tests/ -v
```

### Frontend Tests
```bash
cd frontend
npm test
```

### Integration Tests
```bash
# Run full test suite
npm run test:integration
```

## 📊 Monitoring & Analytics

### Health Checks
- Backend: `GET /api/health`
- Database connectivity
- Azure services status
- AI service availability

### Logging
- Application logs with structured logging
- Error tracking and monitoring
- Performance metrics
- User activity analytics

## 🔐 Security

### Authentication
- JWT tokens with configurable expiration
- OTP-based email verification
- Secure password-less authentication

### Data Protection
- File upload validation and sanitization
- SQL injection prevention
- XSS protection
- CORS configuration
- Rate limiting

### Privacy
- GDPR compliance with data export/deletion
- Secure file storage in Azure
- Encrypted data transmission
- User consent management

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Common Issues

1. **CORS errors**: Check frontend API URL configuration
2. **Database connection**: Verify DATABASE_URL environment variable
3. **File upload issues**: Check file size limits and supported formats
4. **AI processing errors**: Verify OpenAI API key and quota

### Getting Help

- Create an issue on GitHub
- Check the API documentation at `/api/docs`
- Review the troubleshooting guide in the wiki

## 🗺️ Roadmap

### Upcoming Features
- [ ] Integration with job portals (LinkedIn, Indeed)
- [ ] Advanced AI models for better customization
- [ ] Resume templates and formatting options
- [ ] Collaborative resume editing
- [ ] Mobile application
- [ ] Multi-language support
- [ ] Resume performance analytics
- [ ] Interview preparation suggestions

### Technical Improvements
- [ ] Microservices architecture
- [ ] GraphQL API
- [ ] Real-time notifications
- [ ] Advanced caching strategies
- [ ] Machine learning model training
- [ ] Automated testing pipeline

## 👥 Team

- **Backend Development**: FastAPI, Azure, AI Integration
- **Frontend Development**: React, Material-UI, UX/UI
- **DevOps**: Docker, Azure, CI/CD
- **AI/ML**: Resume analysis, job matching algorithms

---

**Built with ❤️ for job seekers worldwide**
