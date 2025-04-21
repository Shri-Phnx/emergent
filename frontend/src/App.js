import { useState, useRef } from "react";
import "./App.css";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

function App() {
  const [linkedinUrl, setLinkedinUrl] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [error, setError] = useState(null);
  const [uploadError, setUploadError] = useState(null);
  const [profileData, setProfileData] = useState(null);
  const [analysisResults, setAnalysisResults] = useState(null);
  const [contentSuggestions, setContentSuggestions] = useState(null);
  const [activeTab, setActiveTab] = useState("analysis");
  const [optimizedSections, setOptimizedSections] = useState(null);
  const [brandingPlan, setBrandingPlan] = useState(null);
  const fileInputRef = useRef(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setProfileData(null);
    setAnalysisResults(null);
    setContentSuggestions(null);

    try {
      const response = await fetch(`${BACKEND_URL}/api/fetch-profile`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ linkedin_url: linkedinUrl }),
      });

      if (!response.ok) {
        throw new Error("Failed to fetch profile data");
      }

      const data = await response.json();
      setProfileData(data.profile_data);
      setAnalysisResults(data.analysis_results);
      setContentSuggestions(data.content_suggestions);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    setUploadLoading(true);
    setUploadError(null);

    try {
      const response = await fetch(`${BACKEND_URL}/api/upload-resume`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Failed to upload resume");
      }

      const data = await response.json();
      setOptimizedSections(data.optimized_sections);
      setBrandingPlan(data.branding_plan);
      setActiveTab("optimization");
    } catch (err) {
      setUploadError(err.message);
    } finally {
      setUploadLoading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-white shadow-sm">
        <div className="container mx-auto px-4 py-6">
          <h1 className="text-3xl font-bold text-gray-900">LinkedIn Profile Analyzer</h1>
          <p className="text-gray-600 mt-2">Optimize your profile and enhance your personal brand</p>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <div className="space-y-8">
          <section className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-2xl font-semibold text-gray-800 mb-4">Analyze Your LinkedIn Profile</h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="linkedin-url" className="block text-gray-700 mb-2">
                  Enter your LinkedIn profile URL
                </label>
                <input
                  type="url"
                  id="linkedin-url"
                  value={linkedinUrl}
                  onChange={(e) => setLinkedinUrl(e.target.value)}
                  placeholder="https://www.linkedin.com/in/username"
                  className="w-full px-4 py-2 border rounded-md focus:ring-blue-500 focus:border-blue-500"
                  required
                />
              </div>
              <button
                type="submit"
                disabled={isLoading}
                className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
              >
                {isLoading ? "Analyzing..." : "Analyze Profile"}
              </button>
              {error && (
                <div className="mt-2 p-3 bg-red-100 text-red-700 rounded-md">{error}</div>
              )}
            </form>
          </section>

          {profileData && (
            <section className="bg-white rounded-lg shadow-md p-6">
              <div className="flex border-b border-gray-200">
                <div className="flex">
                  <button
                    className={`px-4 py-2 font-medium ${
                      activeTab === "analysis" ? "text-blue-600 border-b-2 border-blue-600" : "text-gray-500 hover:text-gray-700"
                    }`}
                    onClick={() => setActiveTab("analysis")}
                  >
                    Analysis Results
                  </button>
                  <button
                    className={`px-4 py-2 font-medium ${
                      activeTab === "content" ? "text-blue-600 border-b-2 border-blue-600" : "text-gray-500 hover:text-gray-700"
                    }`}
                    onClick={() => setActiveTab("content")}
                  >
                    Content Suggestions
                  </button>
                  {optimizedSections && (
                    <button
                      className={`px-4 py-2 font-medium ${
                        activeTab === "optimization" ? "text-blue-600 border-b-2 border-blue-600" : "text-gray-500 hover:text-gray-700"
                      }`}
                      onClick={() => setActiveTab("optimization")}
                    >
                      Optimized Profile
                    </button>
                  )}
                  {brandingPlan && (
                    <button
                      className={`px-4 py-2 font-medium ${
                        activeTab === "branding" ? "text-blue-600 border-b-2 border-blue-600" : "text-gray-500 hover:text-gray-700"
                      }`}
                      onClick={() => setActiveTab("branding")}
                    >
                      Branding Plan
                    </button>
                  )}
                </div>
              </div>

              <div className="mt-6">
                {activeTab === "analysis" && analysisResults && (
                  <div className="space-y-6">
                    <div>
                      <h3 className="text-xl font-semibold mb-3">Overall Profile Score</h3>
                      <div className="flex items-center">
                        <div className="w-16 h-16 rounded-full bg-blue-100 flex items-center justify-center">
                          <span className="text-2xl font-bold text-blue-600">
                            {analysisResults.overall_score}%
                          </span>
                        </div>
                      </div>
                    </div>

                    <div>
                      <h3 className="text-xl font-semibold mb-3">Score Categories</h3>
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {Object.entries(analysisResults.score_categories).map(([category, score]) => (
                          <div key={category} className="bg-gray-50 p-4 rounded-lg">
                            <h4 className="font-medium text-gray-700 capitalize">{category.replace("_", " ")}</h4>
                            <p className="text-2xl font-semibold text-blue-600 mt-2">{score}%</p>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div>
                      <h3 className="text-xl font-semibold mb-3">Section Analysis</h3>
                      <div className="space-y-4">
                        {Object.entries(analysisResults.sections).map(([section, analysis]) => (
                          <div key={section} className="bg-gray-50 p-4 rounded-lg">
                            <h4 className="font-medium text-gray-700 capitalize mb-2">
                              {section.replace("_", " ")}
                            </h4>
                            <p className="text-gray-600">{analysis.feedback ? analysis.feedback.join(". ") : ""}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {activeTab === "content" && contentSuggestions && (
                  <div className="space-y-6">
                    {contentSuggestions.map((suggestion, index) => (
                      <div key={index} className="bg-gray-50 p-4 rounded-lg">
                        <h3 className="font-medium text-gray-700 mb-2">{suggestion.title}</h3>
                        <p className="text-gray-600">{suggestion.content}</p>
                      </div>
                    ))}
                  </div>
                )}

                {activeTab === "optimization" && optimizedSections && (
                  <div className="space-y-6">
                    <div>
                      <h3 className="text-xl font-semibold mb-3">Resume-Optimized LinkedIn Profile</h3>
                      <div className="space-y-4">
                        <div className="bg-gray-50 p-4 rounded-lg">
                          <h4 className="font-medium text-gray-700 mb-2">Professional Headline</h4>
                          <p className="text-gray-600">{optimizedSections.headline}</p>
                        </div>
                        <div className="bg-gray-50 p-4 rounded-lg">
                          <h4 className="font-medium text-gray-700 mb-2">Summary</h4>
                          <p className="text-gray-600 whitespace-pre-line">{optimizedSections.summary}</p>
                        </div>
                        <div className="bg-gray-50 p-4 rounded-lg">
                          <h4 className="font-medium text-gray-700 mb-2">Skills</h4>
                          <div className="flex flex-wrap gap-2">
                            {optimizedSections.skills.map((skill, index) => (
                              <span
                                key={index}
                                className="bg-blue-100 text-blue-700 px-3 py-1 rounded-full text-sm"
                              >
                                {skill}
                              </span>
                            ))}
                          </div>
                        </div>
                        <div className="bg-gray-50 p-4 rounded-lg">
                          <h4 className="font-medium text-gray-700 mb-2">Experience</h4>
                          <div className="space-y-4">
                            {optimizedSections.experience.map((exp, index) => (
                              <div key={index} className="border-l-2 border-blue-200 pl-4">
                                <h5 className="font-medium">{exp.title}</h5>
                                <p className="text-gray-600">{exp.company}</p>
                                <p className="text-sm text-gray-500">{exp.date}</p>
                                <ul className="mt-2 list-disc list-inside text-gray-600">
                                  {exp.highlights.map((highlight, idx) => (
                                    <li key={idx}>{highlight}</li>
                                  ))}
                                </ul>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {activeTab === "branding" && brandingPlan && (
                  <div className="space-y-6">
                    <div>
                      <h3 className="text-xl font-semibold mb-3">4-Week Personal Branding Plan</h3>
                      <div className="space-y-4">
                        {brandingPlan.weekly_plan.map((week, index) => (
                          <div key={index} className="bg-gray-50 p-4 rounded-lg">
                            <h4 className="font-medium text-gray-700 mb-2">Week {index + 1}</h4>
                            <ul className="space-y-2">
                              {week.tasks.map((task, idx) => (
                                <li key={idx} className="flex items-start">
                                  <span className="text-blue-500 mr-2">•</span>
                                  <span className="text-gray-600">{task}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div>
                      <h3 className="text-xl font-semibold mb-3">Profile Banner Suggestion</h3>
                      <div className="bg-gray-50 p-4 rounded-lg">
                        <p className="text-gray-600">{brandingPlan.banner_suggestion}</p>
                      </div>
                    </div>

                    <div>
                      <h3 className="text-xl font-semibold mb-3">Content Posting Schedule</h3>
                      <div className="bg-gray-50 p-4 rounded-lg">
                        <ul className="space-y-2">
                          {brandingPlan.posting_schedule.map((item, index) => (
                            <li key={index} className="flex items-start">
                              <span className="text-blue-500 mr-2">•</span>
                              <span className="text-gray-600">{item}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </section>
          )}

          <section className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-2xl font-semibold text-gray-800 mb-4">Upload Your Resume</h2>
            <p className="text-gray-600 mb-4">
              Upload your resume to get personalized optimization suggestions for your LinkedIn profile
            </p>
            <form className="space-y-4">
              <div>
                <label htmlFor="resume" className="block text-gray-700 mb-2">
                  Choose a file
                </label>
                <input
                  type="file"
                  id="resume"
                  ref={fileInputRef}
                  onChange={handleFileUpload}
                  accept=".pdf,.doc,.docx,.txt"
                  className="w-full"
                />
              </div>
              
              {uploadLoading && (
                <div className="text-blue-600">Uploading and analyzing your resume...</div>
              )}
              
              {uploadError && (
                <div className="mt-2 p-3 bg-red-100 text-red-700 rounded-md">{uploadError}</div>
              )}
            </form>
          </section>

          <section className="mt-8 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-lg shadow-md p-6 text-white">
            <h2 className="text-2xl font-semibold mb-3">Why Optimize Your LinkedIn Profile?</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-4">
              <div className="bg-white bg-opacity-10 rounded-lg p-4">
                <h3 className="font-semibold text-xl mb-2">Increase Visibility</h3>
                <p className="text-blue-100">
                  Stand out to recruiters and potential connections with an optimized profile
                </p>
              </div>
              <div className="bg-white bg-opacity-10 rounded-lg p-4">
                <h3 className="font-semibold text-xl mb-2">Professional Growth</h3>
                <p className="text-blue-100">
                  Showcase your expertise and build a strong professional network
                </p>
              </div>
              <div className="bg-white bg-opacity-10 rounded-lg p-4">
                <h3 className="font-semibold text-xl mb-2">Career Opportunities</h3>
                <p className="text-blue-100">
                  Attract better job opportunities and business partnerships
                </p>
              </div>
            </div>
          </section>
        </div>
      </main>

      <footer className="bg-gray-800 text-white py-8">
        <div className="container mx-auto px-4">
          <p className="text-center text-gray-400">
            © 2025 LinkedIn Profile Analyzer. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;