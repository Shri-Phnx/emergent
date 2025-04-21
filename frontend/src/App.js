import { useState } from "react";
import "./App.css";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

function App() {
  const [linkedinUrl, setLinkedinUrl] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [profileData, setProfileData] = useState(null);
  const [analysisResults, setAnalysisResults] = useState(null);
  const [contentSuggestions, setContentSuggestions] = useState(null);
  const [activeTab, setActiveTab] = useState("analysis");

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
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
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
        <section className="bg-white rounded-lg shadow-md p-6 mb-8">
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
          <section className="bg-white rounded-lg shadow-md p-6">
            <div className="flex border-b border-gray-200">
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
                    <h3 className="text-xl font-semibold text-gray-800 mb-4">Section Scores</h3>
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
              ) : (
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
              )}
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
