# AI-Powered Resume Update Platform

An intelligent platform that automatically updates resumes to match job descriptions using AI, helping job seekers improve their application success rates.

## 🚀 Features

- **AI Resume Customization**: Automatically updates resumes based on job descriptions
- **Email Authentication**: Secure login with one-time password (OTP) system
- **Azure Cloud Integration**: Scalable backend infrastructure
- **Modern UI/UX**: Beautiful, responsive design for optimal user experience
- **Real-time Processing**: Instant resume updates with AI analysis

## 🏗️ Architecture

- **Frontend**: React.js with TypeScript
- **Backend**: Node.js with Express
- **Database**: Azure Cosmos DB
- **Storage**: Azure Blob Storage
- **Authentication**: Custom email OTP system
- **AI**: OpenAI GPT integration for resume analysis

## 🛠️ Tech Stack

- React 18 + TypeScript
- Node.js + Express
- Azure Cloud Services
- OpenAI API
- Tailwind CSS
- React Router
- Axios

## 📦 Installation

### Prerequisites
- Node.js (v18+)
- Azure account
- OpenAI API key

### Setup
1. Clone the repository
2. Install dependencies:
   ```bash
   npm install
   ```
3. Set up environment variables (see `.env.example`)
4. Start the development server:
   ```bash
   npm run dev
   ```

## 🔧 Configuration

Create a `.env` file with the following variables:
```
AZURE_CONNECTION_STRING=your_azure_connection_string
OPENAI_API_KEY=your_openai_api_key
JWT_SECRET=your_jwt_secret
EMAIL_SERVICE_KEY=your_email_service_key
```

## 📱 Usage

1. **Register/Login**: Use your email to create an account
2. **Upload Resume**: Upload your current resume (PDF/DOCX)
3. **Paste Job Description**: Input the job description you're applying for
4. **AI Analysis**: The system analyzes and updates your resume
5. **Download**: Get your customized resume optimized for the role

## 🎯 MVP Features

- [x] AI resume customization
- [x] Email-based authentication
- [x] Azure cloud infrastructure
- [x] Modern responsive UI
- [x] Real-time processing

## 🔮 Future Enhancements

- Advanced AI features for deeper role analysis
- Integration with job portals
- Resume templates and styling options
- Analytics dashboard
- Multi-language support

## 📄 License

MIT License - see LICENSE file for details
