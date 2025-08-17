import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import toast from 'react-hot-toast';
import { 
  SparklesIcon, 
  DocumentTextIcon,
  ClipboardDocumentIcon,
  ArrowDownTrayIcon,
  EyeIcon,
  ChartBarIcon,
  DocumentPlusIcon
} from '@heroicons/react/24/outline';

interface CustomizationResult {
  customizedResume: string;
  analysis: string;
  customizedResumeId: string;
}

interface SkillsAnalysis {
  matchingSkills: string[];
  missingSkills: string[];
  irrelevantSkills: string[];
  recommendations: string[];
  alignmentScore: number;
  summary: string;
}

const ResumeCustomization: React.FC = () => {
  const { resumeId } = useParams<{ resumeId: string }>();
  const navigate = useNavigate();
  const [jobDescription, setJobDescription] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [jobTitle, setJobTitle] = useState('');
  const [customizationResult, setCustomizationResult] = useState<CustomizationResult | null>(null);
  const [skillsAnalysis, setSkillsAnalysis] = useState<SkillsAnalysis | null>(null);
  const [coverLetter, setCoverLetter] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'customize' | 'skills' | 'cover-letter'>('customize');

  const handleCustomizeResume = async () => {
    if (!jobDescription.trim()) {
      toast.error('Please enter a job description');
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post('/api/ai/customize-resume', {
        resumeId,
        jobDescription
      });

      setCustomizationResult(response.data);
      toast.success('Resume customized successfully!');
    } catch (error: any) {
      const message = error.response?.data?.error || 'Failed to customize resume';
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyzeSkills = async () => {
    if (!jobDescription.trim()) {
      toast.error('Please enter a job description');
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post('/api/ai/analyze-skills', {
        resumeId,
        jobDescription
      });

      setSkillsAnalysis(response.data.analysis);
      toast.success('Skills analysis completed!');
    } catch (error: any) {
      const message = error.response?.data?.error || 'Failed to analyze skills';
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateCoverLetter = async () => {
    if (!jobDescription.trim() || !companyName.trim() || !jobTitle.trim()) {
      toast.error('Please fill in all fields');
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post('/api/ai/generate-cover-letter', {
        resumeId,
        jobDescription,
        companyName,
        jobTitle
      });

      setCoverLetter(response.data.coverLetter);
      toast.success('Cover letter generated successfully!');
    } catch (error: any) {
      const message = error.response?.data?.error || 'Failed to generate cover letter';
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  const downloadCustomizedResume = () => {
    if (!customizationResult) return;

    const element = document.createElement('a');
    const file = new Blob([customizationResult.customizedResume], { type: 'text/plain' });
    element.href = URL.createObjectURL(file);
    element.download = 'customized_resume.txt';
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard!');
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">AI Resume Customization</h1>
        <p className="text-gray-600">
          Customize your resume to match specific job descriptions using AI
        </p>
      </div>

      {/* Tabs */}
      <div className="mb-6">
        <nav className="flex space-x-8">
          {[
            { id: 'customize', name: 'Customize Resume', icon: SparklesIcon },
            { id: 'skills', name: 'Skills Analysis', icon: ChartBarIcon },
            { id: 'cover-letter', name: 'Cover Letter', icon: DocumentPlusIcon }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center space-x-2 py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === tab.id
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <tab.icon className="h-5 w-5" />
              <span>{tab.name}</span>
            </button>
          ))}
        </nav>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Input Section */}
        <div className="space-y-6">
          <div className="card">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Job Information</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Job Title
                </label>
                <input
                  type="text"
                  value={jobTitle}
                  onChange={(e) => setJobTitle(e.target.value)}
                  className="input-field"
                  placeholder="e.g., Senior Software Engineer"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Company Name
                </label>
                <input
                  type="text"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  className="input-field"
                  placeholder="e.g., Google, Microsoft"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Job Description
                </label>
                <textarea
                  value={jobDescription}
                  onChange={(e) => setJobDescription(e.target.value)}
                  rows={12}
                  className="input-field resize-none"
                  placeholder="Paste the job description here..."
                />
              </div>
            </div>

            {/* Action Buttons */}
            <div className="mt-6 space-y-3">
              {activeTab === 'customize' && (
                <button
                  onClick={handleCustomizeResume}
                  disabled={loading || !jobDescription.trim()}
                  className="btn-primary w-full flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                      <span>Customizing...</span>
                    </>
                  ) : (
                    <>
                      <SparklesIcon className="h-5 w-5" />
                      <span>Customize Resume</span>
                    </>
                  )}
                </button>
              )}

              {activeTab === 'skills' && (
                <button
                  onClick={handleAnalyzeSkills}
                  disabled={loading || !jobDescription.trim()}
                  className="btn-primary w-full flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                      <span>Analyzing...</span>
                    </>
                  ) : (
                    <>
                      <ChartBarIcon className="h-5 w-5" />
                      <span>Analyze Skills</span>
                    </>
                  )}
                </button>
              )}

              {activeTab === 'cover-letter' && (
                <button
                  onClick={handleGenerateCoverLetter}
                  disabled={loading || !jobDescription.trim() || !companyName.trim() || !jobTitle.trim()}
                  className="btn-primary w-full flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                      <span>Generating...</span>
                    </>
                  ) : (
                    <>
                      <DocumentPlusIcon className="h-5 w-5" />
                      <span>Generate Cover Letter</span>
                    </>
                  )}
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Results Section */}
        <div className="space-y-6">
          {activeTab === 'customize' && customizationResult && (
            <div className="card">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-gray-900">Customized Resume</h2>
                <div className="flex space-x-2">
                  <button
                    onClick={() => copyToClipboard(customizationResult.customizedResume)}
                    className="btn-secondary flex items-center space-x-1"
                  >
                    <ClipboardDocumentIcon className="h-4 w-4" />
                    <span>Copy</span>
                  </button>
                  <button
                    onClick={downloadCustomizedResume}
                    className="btn-secondary flex items-center space-x-1"
                  >
                    <ArrowDownTrayIcon className="h-4 w-4" />
                    <span>Download</span>
                  </button>
                </div>
              </div>
              
              <div className="bg-gray-50 rounded-lg p-4 max-h-96 overflow-y-auto">
                <pre className="whitespace-pre-wrap text-sm text-gray-800 font-mono">
                  {customizationResult.customizedResume}
                </pre>
              </div>

              <div className="mt-4">
                <h3 className="font-semibold text-gray-900 mb-2">Analysis</h3>
                <div className="bg-blue-50 rounded-lg p-4">
                  <p className="text-sm text-gray-700">{customizationResult.analysis}</p>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'skills' && skillsAnalysis && (
            <div className="card">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Skills Analysis</h2>
              
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-700">Alignment Score</span>
                  <span className="text-2xl font-bold text-primary-600">
                    {skillsAnalysis.alignmentScore}/10
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-green-50 rounded-lg p-4">
                    <h4 className="font-semibold text-green-800 mb-2">Matching Skills</h4>
                    <div className="flex flex-wrap gap-1">
                      {skillsAnalysis.matchingSkills.map((skill, index) => (
                        <span key={index} className="bg-green-100 text-green-800 px-2 py-1 rounded text-xs">
                          {skill}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="bg-yellow-50 rounded-lg p-4">
                    <h4 className="font-semibold text-yellow-800 mb-2">Missing Skills</h4>
                    <div className="flex flex-wrap gap-1">
                      {skillsAnalysis.missingSkills.map((skill, index) => (
                        <span key={index} className="bg-yellow-100 text-yellow-800 px-2 py-1 rounded text-xs">
                          {skill}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="bg-blue-50 rounded-lg p-4">
                  <h4 className="font-semibold text-blue-800 mb-2">Recommendations</h4>
                  <ul className="text-sm text-blue-700 space-y-1">
                    {skillsAnalysis.recommendations.map((rec, index) => (
                      <li key={index}>• {rec}</li>
                    ))}
                  </ul>
                </div>

                <div className="bg-gray-50 rounded-lg p-4">
                  <h4 className="font-semibold text-gray-800 mb-2">Summary</h4>
                  <p className="text-sm text-gray-700">{skillsAnalysis.summary}</p>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'cover-letter' && coverLetter && (
            <div className="card">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-gray-900">Generated Cover Letter</h2>
                <button
                  onClick={() => copyToClipboard(coverLetter)}
                  className="btn-secondary flex items-center space-x-1"
                >
                  <ClipboardDocumentIcon className="h-4 w-4" />
                  <span>Copy</span>
                </button>
              </div>
              
              <div className="bg-gray-50 rounded-lg p-4 max-h-96 overflow-y-auto">
                <pre className="whitespace-pre-wrap text-sm text-gray-800">
                  {coverLetter}
                </pre>
              </div>
            </div>
          )}

          {!customizationResult && activeTab === 'customize' && (
            <div className="card">
              <div className="text-center py-12">
                <SparklesIcon className="mx-auto h-12 w-12 text-gray-400" />
                <h3 className="mt-2 text-sm font-medium text-gray-900">No customization yet</h3>
                <p className="mt-1 text-sm text-gray-500">
                  Enter a job description and click "Customize Resume" to get started.
                </p>
              </div>
            </div>
          )}

          {!skillsAnalysis && activeTab === 'skills' && (
            <div className="card">
              <div className="text-center py-12">
                <ChartBarIcon className="mx-auto h-12 w-12 text-gray-400" />
                <h3 className="mt-2 text-sm font-medium text-gray-900">No skills analysis yet</h3>
                <p className="mt-1 text-sm text-gray-500">
                  Enter a job description and click "Analyze Skills" to get started.
                </p>
              </div>
            </div>
          )}

          {!coverLetter && activeTab === 'cover-letter' && (
            <div className="card">
              <div className="text-center py-12">
                <DocumentPlusIcon className="mx-auto h-12 w-12 text-gray-400" />
                <h3 className="mt-2 text-sm font-medium text-gray-900">No cover letter yet</h3>
                <p className="mt-1 text-sm text-gray-500">
                  Fill in all fields and click "Generate Cover Letter" to get started.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ResumeCustomization;