const express = require('express');
const multer = require('multer');
const { BlobServiceClient } = require('@azure/storage-blob');
const { v4: uuidv4 } = require('uuid');
const jwt = require('jsonwebtoken');
const pdf = require('pdf-parse');
const mammoth = require('mammoth');

const router = express.Router();

// Azure Blob Storage setup
const blobServiceClient = BlobServiceClient.fromConnectionString(
  process.env.AZURE_STORAGE_CONNECTION_STRING
);
const containerClient = blobServiceClient.getContainerClient('resumes');

// Multer configuration for file upload
const upload = multer({
  storage: multer.memoryStorage(),
  limits: {
    fileSize: 10 * 1024 * 1024, // 10MB limit
  },
  fileFilter: (req, file, cb) => {
    if (file.mimetype === 'application/pdf' || 
        file.mimetype === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document') {
      cb(null, true);
    } else {
      cb(new Error('Only PDF and DOCX files are allowed'), false);
    }
  }
});

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

// Extract text from PDF
const extractTextFromPDF = async (buffer) => {
  try {
    const data = await pdf(buffer);
    return data.text;
  } catch (error) {
    throw new Error('Failed to extract text from PDF');
  }
};

// Extract text from DOCX
const extractTextFromDOCX = async (buffer) => {
  try {
    const result = await mammoth.extractRawText({ buffer });
    return result.value;
  } catch (error) {
    throw new Error('Failed to extract text from DOCX');
  }
};

// Upload resume
router.post('/upload', authenticateToken, upload.single('resume'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'No file uploaded' });
    }

    const { originalname, buffer, mimetype } = req.file;
    const userId = req.user.userId;
    const resumeId = uuidv4();
    const fileName = `${userId}/${resumeId}_${originalname}`;

    // Upload to Azure Blob Storage
    const blockBlobClient = containerClient.getBlockBlobClient(fileName);
    await blockBlobClient.upload(buffer, buffer.length, {
      blobHTTPHeaders: {
        blobContentType: mimetype
      }
    });

    // Extract text content
    let textContent = '';
    if (mimetype === 'application/pdf') {
      textContent = await extractTextFromPDF(buffer);
    } else if (mimetype === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document') {
      textContent = await extractTextFromDOCX(buffer);
    }

    // Store resume metadata (in production, use database)
    const resumeData = {
      id: resumeId,
      userId,
      fileName: originalname,
      blobName: fileName,
      contentType: mimetype,
      size: buffer.length,
      uploadedAt: new Date().toISOString(),
      textContent: textContent.substring(0, 1000) // Store first 1000 chars for preview
    };

    res.json({
      message: 'Resume uploaded successfully',
      resume: resumeData
    });

  } catch (error) {
    console.error('Resume upload error:', error);
    res.status(500).json({ error: 'Failed to upload resume' });
  }
});

// Get user's resumes
router.get('/list', authenticateToken, async (req, res) => {
  try {
    const userId = req.user.userId;
    
    // List blobs for the user
    const userPrefix = `${userId}/`;
    const resumes = [];
    
    for await (const blob of containerClient.listBlobsFlat({ prefix: userPrefix })) {
      const resumeData = {
        id: blob.name.split('/')[1].split('_')[0],
        fileName: blob.name.split('_').slice(1).join('_'),
        blobName: blob.name,
        size: blob.properties.contentLength,
        uploadedAt: blob.properties.createdOn,
        lastModified: blob.properties.lastModified
      };
      resumes.push(resumeData);
    }

    res.json({ resumes });

  } catch (error) {
    console.error('Resume list error:', error);
    res.status(500).json({ error: 'Failed to fetch resumes' });
  }
});

// Get specific resume
router.get('/:resumeId', authenticateToken, async (req, res) => {
  try {
    const { resumeId } = req.params;
    const userId = req.user.userId;
    
    // Find the blob for this resume
    const userPrefix = `${userId}/`;
    let targetBlob = null;
    
    for await (const blob of containerClient.listBlobsFlat({ prefix: userPrefix })) {
      if (blob.name.includes(resumeId)) {
        targetBlob = blob;
        break;
      }
    }

    if (!targetBlob) {
      return res.status(404).json({ error: 'Resume not found' });
    }

    // Get the blob content
    const blockBlobClient = containerClient.getBlockBlobClient(targetBlob.name);
    const downloadResponse = await blockBlobClient.download();
    const chunks = [];
    
    for await (const chunk of downloadResponse.readableStreamBody) {
      chunks.push(chunk);
    }
    
    const buffer = Buffer.concat(chunks);

    res.json({
      resume: {
        id: resumeId,
        fileName: targetBlob.name.split('_').slice(1).join('_'),
        blobName: targetBlob.name,
        size: targetBlob.properties.contentLength,
        uploadedAt: targetBlob.properties.createdOn,
        contentType: targetBlob.properties.contentType,
        content: buffer.toString('base64')
      }
    });

  } catch (error) {
    console.error('Resume fetch error:', error);
    res.status(500).json({ error: 'Failed to fetch resume' });
  }
});

// Delete resume
router.delete('/:resumeId', authenticateToken, async (req, res) => {
  try {
    const { resumeId } = req.params;
    const userId = req.user.userId;
    
    // Find and delete the blob
    const userPrefix = `${userId}/`;
    let targetBlob = null;
    
    for await (const blob of containerClient.listBlobsFlat({ prefix: userPrefix })) {
      if (blob.name.includes(resumeId)) {
        targetBlob = blob;
        break;
      }
    }

    if (!targetBlob) {
      return res.status(404).json({ error: 'Resume not found' });
    }

    const blockBlobClient = containerClient.getBlockBlobClient(targetBlob.name);
    await blockBlobClient.delete();

    res.json({ message: 'Resume deleted successfully' });

  } catch (error) {
    console.error('Resume deletion error:', error);
    res.status(500).json({ error: 'Failed to delete resume' });
  }
});

module.exports = router;