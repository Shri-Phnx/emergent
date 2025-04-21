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

    try {
      if (!linkedinUrl.includes("linkedin.com/in/")) {
        throw new Error("Please enter a valid LinkedIn profile URL (e.g., https://www.linkedin.com/in/username)");
      }

      const response = await fetch(`${BACKEND_URL}/api/fetch-profile`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ linkedin_url: linkedinUrl }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to fetch profile data");
      }

      const data = await response.json();
      setProfileData(data.profile_data);
      setAnalysisResults(data.analysis_results);
      setContentSuggestions(data.content_suggestions);
      
      // Reset any previous resume analysis results
      setOptimizedSections(null);
      setBrandingPlan(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleResumeUpload = async (e) => {
    e.preventDefault();
    if (!profileData) {
      setUploadError("Please analyze your LinkedIn profile first");
      return;
    }
    
    const file = fileInputRef.current.files[0];
    if (!file) {
      setUploadError("Please select a resume file to upload");
      return;
    }
    
    setUploadLoading(true);
    setUploadError(null);
    
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("profile_id", profileData.profile_id);
      
      const response = await fetch(`${BACKEND_URL}/api/upload-resume`, {
        method: "POST",
        body: formData,
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to process resume");
      }
      
      const data = await response.json();
      setOptimizedSections(data.optimized_sections);
      setBrandingPlan(data.branding_plan);
      
      // Switch to the optimization tab to show results
      setActiveTab("optimization");
    } catch (err) {
      setUploadError(err.message);
    } finally {
      setUploadLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-blue-100">
      <header className="bg-white shadow-md">
        <div className="container mx-auto px-4 py-6">
          <h1 className="text-3xl font-bold text-blue-600">LinkedIn Profile Analyzer</h1>
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
                id="linkedin-url"
                type="text"
                value={linkedinUrl}
                onChange={(e) => setLinkedinUrl(e.target.value)}
                placeholder="https://www.linkedin.com/in/username"
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>
            <button
              type="submit"
              disabled={isLoading}
              className="px-6 py-2 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? "Analyzing..." : "Analyze Profile"}
            </button>
          </form>
          {error && <div className="mt-4 p-3 bg-red-100 text-red-700 rounded-md">{error}</div>}
        </section>

        {profileData && analysisResults && (
          <section className="bg-white rounded-lg shadow-md p-6 mb-6">
            <h2 className="text-2xl font-semibold text-gray-800 mb-4">Optimize with Your Resume</h2>
            <p className="text-gray-600 mb-4">Upload your resume to get personalized improvement suggestions for your LinkedIn profile.</p>
            
            <form onSubmit={handleResumeUpload} className="space-y-4">
              <div>
                <label htmlFor="resume-file" className="block text-gray-700 mb-2">
                  Select your resume file (PDF, DOC, DOCX, or TXT)
                </label>
                <input
                  id="resume-file"
                  type="file"
                  ref={fileInputRef}
                  accept=".pdf,.doc,.docx,.txt"
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-gray-700"
                />
              </div>
              
              <button
                type="submit"
                disabled={uploadLoading || !profileData}
                className="px-6 py-2 bg-green-600 text-white font-medium rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {uploadLoading ? "Processing..." : "Optimize My Profile"}
              </button>
              
              {!profileData && (
                <p className="text-amber-600 text-sm mt-2">Please analyze your LinkedIn profile first.</p>
              )}
              
              {uploadError && (
                <div className="mt-2 p-3 bg-red-100 text-red-700 rounded-md">{uploadError}</div>
              )}
            </form>
          </section>
          
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
              {activeTab === "analysis" ? (
                <div>
                  <div className="mb-6">
                    <h3 className="text-xl font-semibold text-gray-800 mb-2">Overall Profile Score</h3>
                    <div className="flex items-center">
                      <div className="w-full bg-gray-200 rounded-full h-4 mr-4">
                        <div
                          className="bg-blue-600 h-4 rounded-full"
                          style={{ width: `${analysisResults.overall_score}%` }}
                        ></div>
                      </div>
                      <span className="text-lg font-semibold">{Math.round(analysisResults.overall_score)}%</span>
                    </div>
                  </div>
                  
                  <div className="mb-6">
                    <h3 className="text-xl font-semibold text-gray-800 mb-2">Scoring Categories</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                      {Object.entries(analysisResults.score_categories).map(([category, score]) => (
                        <div key={category} className="bg-white shadow-sm rounded-lg p-4 border border-gray-200">
                          <h5 className="text-md font-medium text-gray-700 capitalize mb-1">{category}</h5>
                          <div className="flex items-center">
                            <div className="w-full bg-gray-200 rounded-full h-3 mr-2">
                              <div 
                                className={`h-3 rounded-full ${
                                  category === "completeness" ? "bg-green-500" : 
                                  category === "relevance" ? "bg-blue-500" :
                                  category === "impact" ? "bg-purple-500" : "bg-yellow-500"
                                }`}
                                style={{ width: `${score}%` }}
                              ></div>
                            </div>
                            <span className="text-sm font-semibold">{Math.round(score)}/25</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="mb-6">
                    <h3 className="text-xl font-semibold text-gray-800 mb-4">Section Analysis</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {Object.entries(analysisResults.sections).map(([section, data]) => (
                        <div key={section} className="border border-gray-200 rounded-md p-4">
                          <div className="flex justify-between items-center mb-2">
                            <h4 className="text-lg font-medium capitalize">{section}</h4>
                            <span className="text-lg font-semibold">{Math.round(data.score)}%</span>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-3 mb-3">
                            <div
                              className="bg-blue-600 h-3 rounded-full"
                              style={{ width: `${data.score}%` }}
                            ></div>
                          </div>
                          
                          {data.category_scores && (
                            <div className="grid grid-cols-2 gap-2 mb-3">
                              {Object.entries(data.category_scores).map(([category, score]) => (
                                <div key={category} className="flex items-center">
                                  <div className="w-2 h-2 rounded-full mr-1.5 flex-shrink-0" 
                                    style={{
                                      backgroundColor: 
                                        category === "completeness" ? "#10B981" : 
                                        category === "relevance" ? "#3B82F6" :
                                        category === "impact" ? "#8B5CF6" : "#F59E0B"
                                    }}
                                  ></div>
                                  <span className="text-xs text-gray-600 capitalize mr-1">{category}:</span>
                                  <span className="text-xs font-medium">{Math.round(score)}/25</span>
                                </div>
                              ))}
                            </div>
                          )}
                          
                          <ul className="space-y-1 text-sm text-gray-600">
                            {data.feedback.map((item, index) => (
                              <li key={index} className="flex items-start">
                                <span className="mr-2">•</span>
                                <span>{item}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <h3 className="text-xl font-semibold text-gray-800 mb-3">Overall Recommendations</h3>
                    <ul className="space-y-2">
                      {analysisResults.overall_recommendations.map((recommendation, index) => (
                        <li key={index} className="flex items-start bg-blue-50 p-3 rounded-md">
                          <span className="mr-2 text-blue-600">✓</span>
                          <span>{recommendation}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              ) : activeTab === "content" ? (
                <div>
                  <h3 className="text-xl font-semibold text-gray-800 mb-4">Content Suggestions for LinkedIn Posts</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {contentSuggestions.map((suggestion, index) => (
                      <div
                        key={index}
                        className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-100 rounded-lg p-4 hover:shadow-md transition-shadow"
                      >
                        <h4 className="font-medium text-blue-800 mb-2">Content Idea {index + 1}</h4>
                        <p className="text-gray-700">{suggestion}</p>
                      </div>
                    ))}
                  </div>
                </div>
              ) : activeTab === "optimization" ? (
                <div>
                  <h3 className="text-xl font-semibold text-gray-800 mb-4">Resume-Optimized LinkedIn Profile</h3>
                  
                  {/* Headline Optimization */}
                  <div className="mb-8 border border-gray-200 rounded-lg p-5 bg-white">
                    <h4 className="text-lg font-medium text-gray-800 mb-3">Headline Optimization</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div className="bg-gray-50 p-4 rounded-md">
                        <h5 className="font-medium text-gray-700 mb-2">Current Headline</h5>
                        <p className="text-gray-600">{optimizedSections.headline.current || "No headline provided"}</p>
                      </div>
                      <div className="bg-green-50 p-4 rounded-md border border-green-100">
                        <h5 className="font-medium text-green-700 mb-2">Optimized Headline</h5>
                        <p className="text-gray-700 font-semibold">{optimizedSections.headline.optimized}</p>
                        
                        {optimizedSections.headline.alternatives && optimizedSections.headline.alternatives.length > 0 && (
                          <div className="mt-3">
                            <h6 className="text-sm font-medium text-gray-700">Alternative Options:</h6>
                            <ul className="mt-1 space-y-1">
                              {optimizedSections.headline.alternatives.map((alt, index) => (
                                <li key={index} className="text-sm text-gray-600 flex items-start">
                                  <span className="mr-1">•</span>
                                  <span>{alt}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                  
                  {/* Summary Optimization */}
                  <div className="mb-8 border border-gray-200 rounded-lg p-5 bg-white">
                    <h4 className="text-lg font-medium text-gray-800 mb-3">About/Summary Optimization</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div className="bg-gray-50 p-4 rounded-md">
                        <h5 className="font-medium text-gray-700 mb-2">Current Summary</h5>
                        <div className="text-gray-600 whitespace-pre-line">{optimizedSections.summary.current || "No summary provided"}</div>
                      </div>
                      <div className="bg-green-50 p-4 rounded-md border border-green-100">
                        <h5 className="font-medium text-green-700 mb-2">Optimized Summary</h5>
                        <div className="text-gray-700 whitespace-pre-line">{optimizedSections.summary.optimized}</div>
                      </div>
                    </div>
                  </div>
                  
                  {/* Skills Optimization */}
                  <div className="mb-8 border border-gray-200 rounded-lg p-5 bg-white">
                    <h4 className="text-lg font-medium text-gray-800 mb-3">Skills Optimization</h4>
                    
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                      <div className="bg-gray-50 p-4 rounded-md">
                        <h5 className="font-medium text-gray-700 mb-2">Current Skills</h5>
                        <div className="flex flex-wrap gap-2">
                          {optimizedSections.skills.current.map((skill, index) => (
                            <span key={index} className="inline-flex bg-gray-200 text-gray-700 rounded-md px-2 py-1 text-sm">
                              {skill}
                            </span>
                          ))}
                        </div>
                      </div>
                      
                      <div className="bg-green-50 p-4 rounded-md border border-green-100">
                        <h5 className="font-medium text-green-700 mb-2">Prioritized Skills</h5>
                        <div className="flex flex-wrap gap-2">
                          {optimizedSections.skills.prioritized.map((skill, index) => (
                            <span key={index} className="inline-flex bg-green-200 text-green-800 rounded-md px-2 py-1 text-sm">
                              {skill}
                            </span>
                          ))}
                        </div>
                      </div>
                      
                      <div className="bg-blue-50 p-4 rounded-md border border-blue-100">
                        <h5 className="font-medium text-blue-700 mb-2">Skills to Add from Resume</h5>
                        <div className="flex flex-wrap gap-2">
                          {optimizedSections.skills.missing.length > 0 ? (
                            optimizedSections.skills.missing.map((skill, index) => (
                              <span key={index} className="inline-flex bg-blue-200 text-blue-800 rounded-md px-2 py-1 text-sm">
                                {skill}
                              </span>
                            ))
                          ) : (
                            <p className="text-gray-500 text-sm">No missing skills found</p>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  {/* Featured Section Suggestions */}
                  <div className="mb-8 border border-gray-200 rounded-lg p-5 bg-white">
                    <h4 className="text-lg font-medium text-gray-800 mb-3">Featured Section Optimization</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                      {optimizedSections.featured.map((item, index) => (
                        <div key={index} className="bg-indigo-50 p-4 rounded-md border border-indigo-100">
                          <h5 className="font-medium text-indigo-700 mb-1">{item.type}: {item.title}</h5>
                          <p className="text-gray-600 text-sm">{item.description}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                  
                  {/* Experience Enhancement */}
                  <div className="border border-gray-200 rounded-lg p-5 bg-white">
                    <h4 className="text-lg font-medium text-gray-800 mb-4">Experience Enhancement</h4>
                    {optimizedSections.experience.optimized.map((exp, index) => (
                      <div key={index} className="mb-6 last:mb-0">
                        <h5 className="font-medium text-gray-800 mb-1">{exp.title} at {exp.company}</h5>
                        
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-3">
                          <div className="bg-gray-50 p-4 rounded-md">
                            <h6 className="text-sm font-medium text-gray-700 mb-2">Current Description</h6>
                            <div className="text-gray-600 text-sm whitespace-pre-line">
                              {exp.current_description || "No description provided"}
                            </div>
                          </div>
                          <div className="bg-green-50 p-4 rounded-md border border-green-100">
                            <h6 className="text-sm font-medium text-green-700 mb-2">Enhanced Description</h6>
                            <div className="text-gray-700 text-sm whitespace-pre-line">
                              {exp.enhanced_description}
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : activeTab === "branding" ? (
                <div>
                  <h3 className="text-xl font-semibold text-gray-800 mb-4">Personal Branding Plan</h3>
                  
                  {/* Banner Suggestion */}
                  <div className="mb-8 border border-gray-200 rounded-lg p-5 bg-white">
                    <h4 className="text-lg font-medium text-gray-800 mb-3">Banner Image Suggestion</h4>
                    <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-4 rounded-md border border-blue-100">
                      <h5 className="font-medium text-blue-700 mb-2">{brandingPlan.banner_suggestion.theme}</h5>
                      <div className="mb-3">
                        <h6 className="text-sm font-medium text-gray-700 mb-1">Recommended Elements:</h6>
                        <ul className="space-y-1">
                          {brandingPlan.banner_suggestion.elements.map((element, index) => (
                            <li key={index} className="text-sm text-gray-600 flex items-start">
                              <span className="mr-1 text-blue-500">•</span>
                              <span>{element}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                      <div>
                        <h6 className="text-sm font-medium text-gray-700 mb-1">Color Palette:</h6>
                        <div className="flex gap-2 mt-1">
                          {brandingPlan.banner_suggestion.colors.map((color, index) => (
                            <div 
                              key={index}
                              className="w-8 h-8 rounded-full border border-gray-300" 
                              style={{ backgroundColor: color }}
                              title={color}
                            ></div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  {/* 4-Week Plan */}
                  <div className="border border-gray-200 rounded-lg p-5 bg-white">
                    <h4 className="text-lg font-medium text-gray-800 mb-4">4-Week Branding Plan</h4>
                    <p className="text-gray-600 mb-5">{brandingPlan.posting_schedule}</p>
                    
                    <div className="space-y-6">
                      {brandingPlan.weekly_plan.map((week) => (
                        <div key={week.week} className="border-l-4 border-indigo-500 pl-4 py-1">
                          <h5 className="font-medium text-gray-800 mb-2">Week {week.week}: {week.theme}</h5>
                          
                          {week.tasks && (
                            <div className="mb-3">
                              <h6 className="text-sm font-medium text-gray-700 mb-1">Tasks:</h6>
                              <ul className="space-y-1">
                                {week.tasks.map((task, index) => (
                                  <li key={index} className="text-sm text-gray-600 flex items-start">
                                    <span className="mr-1 text-indigo-500">✓</span>
                                    <span>{task}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                          
                          {week.posts && (
                            <div className="mb-3">
                              <h6 className="text-sm font-medium text-gray-700 mb-1">Content Ideas:</h6>
                              <ul className="space-y-1">
                                {week.posts.map((post, index) => (
                                  <li key={index} className="text-sm text-gray-600 flex items-start">
                                    <span className="mr-1 text-indigo-500">•</span>
                                    <span>{post}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                          
                          {week.frequency && (
                            <p className="text-sm text-indigo-600 font-medium">{week.frequency}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ) : null}
            </div>
          </section>
        )}

        <section className="mt-8 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-lg shadow-md p-6 text-white">
          <h2 className="text-2xl font-semibold mb-3">Why Optimize Your LinkedIn Profile?</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-4">
            <div className="bg-white bg-opacity-10 rounded-lg p-4">
              <h3 className="font-semibold text-xl mb-2">Increase Visibility</h3>
              <p className="text-blue-100">
                An optimized profile helps you appear in search results and gets you noticed by recruiters and potential clients.
              </p>
            </div>
            <div className="bg-white bg-opacity-10 rounded-lg p-4">
              <h3 className="font-semibold text-xl mb-2">Build Credibility</h3>
              <p className="text-blue-100">
                Showcase your expertise and achievements to establish yourself as a trusted professional in your field.
              </p>
            </div>
            <div className="bg-white bg-opacity-10 rounded-lg p-4">
              <h3 className="font-semibold text-xl mb-2">Grow Your Network</h3>
              <p className="text-blue-100">
                Connect with like-minded professionals, potential employers, and industry leaders to expand your opportunities.
              </p>
            </div>
          </div>
        </section>
      </main>

      <footer className="bg-gray-800 text-white py-6">
        <div className="container mx-auto px-4">
          <p className="text-center">© {new Date().getFullYear()} LinkedIn Profile Analyzer | Enhance Your Professional Brand</p>
        </div>
      </footer>
    </div>
  );
}

export default App;
