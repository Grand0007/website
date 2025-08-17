const express = require('express');
const { body, validationResult } = require('express-validator');
const OpenAI = require('openai');
const jwt = require('jsonwebtoken');
const { BlobServiceClient } = require('@azure/storage-blob');
const { v4: uuidv4 } = require('uuid');

const router = express.Router();

// OpenAI setup
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY
});

// Azure Blob Storage setup
const blobServiceClient = BlobServiceClient.fromConnectionString(
  process.env.AZURE_STORAGE_CONNECTION_STRING
);
const containerClient = blobServiceClient.getContainerClient('resumes');

// Middleware to verify JWT token
const authenticateToken = (req, res, next) => {
  const token = req.headers.authorization?.split(' ')[1];
  
  if (!token) {
    return res.status(401).json({ error: 'Access token required' });
  }

  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    req.user = decoded;
    next();
  } catch (error) {
    return res.status(403).json({ error: 'Invalid token' });
  }
};

// Get resume content from Azure
const getResumeContent = async (resumeId, userId) => {
  const userPrefix = `${userId}/`;
  let targetBlob = null;
  
  for await (const blob of containerClient.listBlobsFlat({ prefix: userPrefix })) {
    if (blob.name.includes(resumeId)) {
      targetBlob = blob;
      break;
    }
  }

  if (!targetBlob) {
    throw new Error('Resume not found');
  }

  const blockBlobClient = containerClient.getBlockBlobClient(targetBlob.name);
  const downloadResponse = await blockBlobClient.download();
  const chunks = [];
  
  for await (const chunk of downloadResponse.readableStreamBody) {
    chunks.push(chunk);
  }
  
  return Buffer.concat(chunks);
};

// AI-powered resume customization
router.post('/customize-resume', 
  authenticateToken,
  body('resumeId').notEmpty(),
  body('jobDescription').notEmpty().isLength({ min: 50 }),
  async (req, res) => {
    try {
      const errors = validationResult(req);
      if (!errors.isEmpty()) {
        return res.status(400).json({ errors: errors.array() });
      }

      const { resumeId, jobDescription } = req.body;
      const userId = req.user.userId;

      // Get resume content
      const resumeBuffer = await getResumeContent(resumeId, userId);
      const resumeText = resumeBuffer.toString('utf-8');

      // Create AI prompt for resume customization
      const prompt = `
You are an expert resume writer and career coach. Your task is to customize a resume to better match a specific job description.

ORIGINAL RESUME:
${resumeText}

JOB DESCRIPTION:
${jobDescription}

Please analyze the job description and customize the resume to:
1. Highlight relevant skills and experiences that match the job requirements
2. Use keywords from the job description that are relevant to the candidate's experience
3. Reorganize content to prioritize the most relevant information
4. Maintain professional tone and formatting
5. Keep the same basic structure but enhance content alignment

Provide the customized resume content in a clean, professional format. Focus on making the candidate appear as the ideal fit for this specific role.

CUSTOMIZED RESUME:
`;

      // Call OpenAI API
      const completion = await openai.chat.completions.create({
        model: "gpt-4",
        messages: [
          {
            role: "system",
            content: "You are an expert resume writer specializing in ATS-optimized resumes and job-specific customization."
          },
          {
            role: "user",
            content: prompt
          }
        ],
        max_tokens: 2000,
        temperature: 0.7
      });

      const customizedResume = completion.choices[0].message.content;

      // Generate analysis of changes
      const analysisPrompt = `
Analyze the customization made to the resume and provide a brief summary of the key changes made to better align with the job description.

ORIGINAL RESUME:
${resumeText}

CUSTOMIZED RESUME:
${customizedResume}

JOB DESCRIPTION:
${jobDescription}

Please provide a concise analysis (2-3 paragraphs) explaining:
1. Key skills and experiences that were emphasized
2. Keywords that were incorporated
3. Overall improvements made for this specific role

ANALYSIS:
`;

      const analysisCompletion = await openai.chat.completions.create({
        model: "gpt-4",
        messages: [
          {
            role: "system",
            content: "You are a career coach providing resume analysis and feedback."
          },
          {
            role: "user",
            content: analysisPrompt
          }
        ],
        max_tokens: 500,
        temperature: 0.5
      });

      const analysis = analysisCompletion.choices[0].message.content;

      // Save customized resume to Azure
      const customizedResumeId = uuidv4();
      const fileName = `${userId}/${customizedResumeId}_customized_resume.txt`;
      const blockBlobClient = containerClient.getBlockBlobClient(fileName);
      
      await blockBlobClient.upload(customizedResume, customizedResume.length, {
        blobHTTPHeaders: {
          blobContentType: 'text/plain'
        }
      });

      res.json({
        message: 'Resume customized successfully',
        customizedResume,
        analysis,
        customizedResumeId,
        fileName
      });

    } catch (error) {
      console.error('Resume customization error:', error);
      res.status(500).json({ error: 'Failed to customize resume' });
    }
  }
);

// Get skills analysis
router.post('/analyze-skills',
  authenticateToken,
  body('resumeId').notEmpty(),
  body('jobDescription').notEmpty(),
  async (req, res) => {
    try {
      const errors = validationResult(req);
      if (!errors.isEmpty()) {
        return res.status(400).json({ errors: errors.array() });
      }

      const { resumeId, jobDescription } = req.body;
      const userId = req.user.userId;

      // Get resume content
      const resumeBuffer = await getResumeContent(resumeId, userId);
      const resumeText = resumeBuffer.toString('utf-8');

      const skillsPrompt = `
Analyze the resume and job description to provide a comprehensive skills analysis.

RESUME:
${resumeText}

JOB DESCRIPTION:
${jobDescription}

Please provide a detailed analysis including:
1. Skills that match between resume and job description
2. Skills in the job description that are missing from the resume
3. Skills in the resume that are not relevant to this job
4. Recommendations for skills to add or emphasize
5. Overall skills alignment score (1-10)

Format the response as JSON with the following structure:
{
  "matchingSkills": ["skill1", "skill2"],
  "missingSkills": ["skill1", "skill2"],
  "irrelevantSkills": ["skill1", "skill2"],
  "recommendations": ["recommendation1", "recommendation2"],
  "alignmentScore": 8,
  "summary": "Brief summary of skills alignment"
}
`;

      const completion = await openai.chat.completions.create({
        model: "gpt-4",
        messages: [
          {
            role: "system",
            content: "You are a skills analysis expert. Provide responses in valid JSON format only."
          },
          {
            role: "user",
            content: skillsPrompt
          }
        ],
        max_tokens: 1000,
        temperature: 0.3
      });

      const skillsAnalysis = JSON.parse(completion.choices[0].message.content);

      res.json({
        message: 'Skills analysis completed',
        analysis: skillsAnalysis
      });

    } catch (error) {
      console.error('Skills analysis error:', error);
      res.status(500).json({ error: 'Failed to analyze skills' });
    }
  }
);

// Generate cover letter
router.post('/generate-cover-letter',
  authenticateToken,
  body('resumeId').notEmpty(),
  body('jobDescription').notEmpty(),
  body('companyName').notEmpty(),
  body('jobTitle').notEmpty(),
  async (req, res) => {
    try {
      const errors = validationResult(req);
      if (!errors.isEmpty()) {
        return res.status(400).json({ errors: errors.array() });
      }

      const { resumeId, jobDescription, companyName, jobTitle } = req.body;
      const userId = req.user.userId;

      // Get resume content
      const resumeBuffer = await getResumeContent(resumeId, userId);
      const resumeText = resumeBuffer.toString('utf-8');

      const coverLetterPrompt = `
Write a compelling cover letter for the following job application.

CANDIDATE'S RESUME:
${resumeText}

JOB DESCRIPTION:
${jobDescription}

COMPANY: ${companyName}
POSITION: ${jobTitle}

Please write a professional cover letter that:
1. Addresses the hiring manager professionally
2. Explains why the candidate is interested in this specific role and company
3. Highlights relevant experience and skills from the resume
4. Demonstrates understanding of the job requirements
5. Shows enthusiasm and fit for the company culture
6. Includes a call to action

The cover letter should be 3-4 paragraphs and maintain a professional, confident tone.

COVER LETTER:
`;

      const completion = await openai.chat.completions.create({
        model: "gpt-4",
        messages: [
          {
            role: "system",
            content: "You are an expert cover letter writer specializing in personalized, compelling applications."
          },
          {
            role: "user",
            content: coverLetterPrompt
          }
        ],
        max_tokens: 1000,
        temperature: 0.7
      });

      const coverLetter = completion.choices[0].message.content;

      res.json({
        message: 'Cover letter generated successfully',
        coverLetter
      });

    } catch (error) {
      console.error('Cover letter generation error:', error);
      res.status(500).json({ error: 'Failed to generate cover letter' });
    }
  }
);

module.exports = router;