const express = require('express');
const { body, validationResult } = require('express-validator');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const nodemailer = require('nodemailer');
const { v4: uuidv4 } = require('uuid');

const router = express.Router();

// In-memory storage for OTP (in production, use Redis or database)
const otpStore = new Map();
const userStore = new Map();

// Email transporter setup
const transporter = nodemailer.createTransporter({
  service: 'gmail',
  auth: {
    user: process.env.EMAIL_USER,
    pass: process.env.EMAIL_PASSWORD
  }
});

// Generate OTP
const generateOTP = () => {
  return Math.floor(100000 + Math.random() * 900000).toString();
};

// Send OTP email
const sendOTPEmail = async (email, otp) => {
  const mailOptions = {
    from: process.env.EMAIL_USER,
    to: email,
    subject: 'Your Login OTP - AI Resume Updater',
    html: `
      <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #2563eb;">AI Resume Updater</h2>
        <p>Your one-time password (OTP) is:</p>
        <h1 style="color: #2563eb; font-size: 48px; text-align: center; letter-spacing: 8px;">${otp}</h1>
        <p>This OTP will expire in 10 minutes.</p>
        <p>If you didn't request this, please ignore this email.</p>
      </div>
    `
  };

  try {
    await transporter.sendMail(mailOptions);
    return true;
  } catch (error) {
    console.error('Email sending failed:', error);
    return false;
  }
};

// Request OTP
router.post('/request-otp', 
  body('email').isEmail().normalizeEmail(),
  async (req, res) => {
    try {
      const errors = validationResult(req);
      if (!errors.isEmpty()) {
        return res.status(400).json({ errors: errors.array() });
      }

      const { email } = req.body;
      const otp = generateOTP();
      const otpId = uuidv4();

      // Store OTP with expiration (10 minutes)
      otpStore.set(otpId, {
        email,
        otp,
        expiresAt: Date.now() + 10 * 60 * 1000
      });

      // Send OTP email
      const emailSent = await sendOTPEmail(email, otp);
      
      if (!emailSent) {
        return res.status(500).json({ error: 'Failed to send OTP email' });
      }

      res.json({ 
        message: 'OTP sent successfully',
        otpId // In production, don't send this to client
      });

    } catch (error) {
      console.error('OTP request error:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  }
);

// Verify OTP and login
router.post('/verify-otp',
  body('otpId').notEmpty(),
  body('otp').isLength({ min: 6, max: 6 }).isNumeric(),
  async (req, res) => {
    try {
      const errors = validationResult(req);
      if (!errors.isEmpty()) {
        return res.status(400).json({ errors: errors.array() });
      }

      const { otpId, otp } = req.body;
      const storedData = otpStore.get(otpId);

      if (!storedData) {
        return res.status(400).json({ error: 'Invalid OTP ID' });
      }

      if (Date.now() > storedData.expiresAt) {
        otpStore.delete(otpId);
        return res.status(400).json({ error: 'OTP expired' });
      }

      if (storedData.otp !== otp) {
        return res.status(400).json({ error: 'Invalid OTP' });
      }

      // OTP is valid, create or get user
      let user = userStore.get(storedData.email);
      if (!user) {
        user = {
          id: uuidv4(),
          email: storedData.email,
          createdAt: new Date().toISOString(),
          resumes: []
        };
        userStore.set(storedData.email, user);
      }

      // Generate JWT token
      const token = jwt.sign(
        { userId: user.id, email: user.email },
        process.env.JWT_SECRET,
        { expiresIn: '7d' }
      );

      // Clean up OTP
      otpStore.delete(otpId);

      res.json({
        message: 'Login successful',
        token,
        user: {
          id: user.id,
          email: user.email,
          createdAt: user.createdAt
        }
      });

    } catch (error) {
      console.error('OTP verification error:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  }
);

// Get user profile
router.get('/profile', async (req, res) => {
  try {
    const token = req.headers.authorization?.split(' ')[1];
    if (!token) {
      return res.status(401).json({ error: 'No token provided' });
    }

    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    const user = userStore.get(decoded.email);

    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }

    res.json({
      user: {
        id: user.id,
        email: user.email,
        createdAt: user.createdAt
      }
    });

  } catch (error) {
    console.error('Profile fetch error:', error);
    res.status(401).json({ error: 'Invalid token' });
  }
});

module.exports = router;