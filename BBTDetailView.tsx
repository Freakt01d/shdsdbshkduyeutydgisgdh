import React, { useState, useEffect } from "react";
import { diffWords } from "diff";
import "./BBTView.scss";

const BBTView: React.FC = () => {
  const [expectedResponse, setExpectedResponse] = useState("");
  const [actualResponse, setActualResponse] = useState("");
  const [diffResult, setDiffResult] = useState<JSX.Element[]>([]);

  // Fetch file content
  const fetchFile = (fileName: string, setFileContent: React.Dispatch<React.SetStateAction<string>>) => {
    fetch(`/xmldata/${fileName}.txt`)
      .then((response) => response.text())
      .then((data) => setFileContent(data))
      .catch((error) => console.error(`Error fetching ${fileName}.txt:`, error));
  };

  // Fetch both expected and actual responses when component loads
  useEffect(() => {
    fetchFile("expectedResponse", setExpectedResponse);
    fetchFile("actualResponse", setActualResponse);
  }, []);

  // Compute the diff whenever responses change
  useEffect(() => {
    if (expectedResponse && actualResponse) {
      const diff = diffWords(expectedResponse, actualResponse);
      const formattedDiff = diff.map((part, index) => {
        let color = "black";
        if (part.added) color = "yellow"; // Added text
        if (part.removed) color = "red"; // Removed text
        if (!part.added && !part.removed && expectedResponse !== actualResponse) color = "green"; // Changed text

        return (
          <span key={index} style={{ backgroundColor: color }}>
            {part.value}
          </span>
        );
      });
      setDiffResult(formattedDiff);
    }
  }, [expectedResponse, actualResponse]);

  return (
    <div className="bbt-view">
      <h3>Response Comparison</h3>
      <div className="diff-container">
        {diffResult.length > 0 ? diffResult : <p>No differences found.</p>}
      </div>
    </div>
  );
};

export default BBTView;