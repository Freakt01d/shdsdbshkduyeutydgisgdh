import React, { useState, useEffect } from "react";
import { diffWords } from "diff";
import "./BBTView.scss";

const BBTView: React.FC = () => {
  const [expectedResponse, setExpectedResponse] = useState("");
  const [actualResponse, setActualResponse] = useState("");
  const [expectedDiff, setExpectedDiff] = useState<JSX.Element[]>([]);
  const [actualDiff, setActualDiff] = useState<JSX.Element[]>([]);

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

      // Process Expected and Actual Response separately
      const expectedFormatted = diff.map((part, index) => {
        if (part.removed) return <span key={index} style={{ backgroundColor: "red" }}>{part.value}</span>; // Removed text
        return <span key={index}>{part.value}</span>; // Unchanged or changed (still shown)
      });

      const actualFormatted = diff.map((part, index) => {
        if (part.added) return <span key={index} style={{ backgroundColor: "yellow" }}>{part.value}</span>; // Added text
        return <span key={index}>{part.value}</span>; // Unchanged or changed (still shown)
      });

      setExpectedDiff(expectedFormatted);
      setActualDiff(actualFormatted);
    }
  }, [expectedResponse, actualResponse]);

  return (
    <div className="bbt-view">
      <h3>Response Comparison</h3>
      <div className="diff-container">
        <div>
          <h4>Expected Response</h4>
          <div className="xml-box">{expectedDiff}</div>
        </div>
        <div>
          <h4>Actual Response</h4>
          <div className="xml-box">{actualDiff}</div>
        </div>
      </div>
    </div>
  );
};

export default BBTView;