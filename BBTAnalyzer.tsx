import React, { useState } from "react";
import "./BBTView.css";

const BBTView: React.FC = () => {
  const [activeTab, setActiveTab] = useState("request");

  return (
    <div className="bbt-view">
      <div className="bbt-header">
        <select className="dropdown">
          <option value="ISO_25.01.31.1">ISO_25.01.31.1</option>
        </select>
        <button className="btn">Start Comparison</button>
        <button className="btn">View Report</button>
        <button className="btn">Email Report</button>
        <button className="btn">Initiate New BBT</button>
        <button className="btn">Add BBT</button>
      </div>
      
      <div className="bbt-tabs">
        <button 
          className={`tab ${activeTab === "request" ? "active" : ""}`} 
          onClick={() => setActiveTab("request")}
        >
          Request XML
        </button>
        <button 
          className={`tab ${activeTab === "response" ? "active" : ""}`} 
          onClick={() => setActiveTab("response")}
        >
          Response XML
        </button>
        <button 
          className={`tab ${activeTab === "comparison" ? "active" : ""}`} 
          onClick={() => setActiveTab("comparison")}
        >
          Response Comparison
        </button>
      </div>

      <div className="bbt-content">
        {activeTab === "request" && (
          <textarea className="xml-box" readOnly>
            {`<Request>
  <Workflow Name="SECFIN" Version="1" Result="true"/>
  <SpecificFields>
    <Field Name="Trader_ID" Value="10000181040"/>
  </SpecificFields>
</Request>`}
          </textarea>
        )}
        {activeTab === "response" && (
          <textarea className="xml-box" readOnly>
            {`<Response>
  <Workflow Name="SECFIN" Version="1" Result="true"/>
  <Flags>
    <Flag Name="Eligible" Value="True"/>
  </Flags>
</Response>`}
          </textarea>
        )}
        {activeTab === "comparison" && (
          <textarea className="xml-box" readOnly>
            {`Differences found:
- Expected: <Flag Name="Eligible" Value="True"/>
- Actual: <Flag Name="Eligible_SEC" Value="True"/>`}
          </textarea>
        )}
      </div>

      <div className="bbt-footer">
        <div className="status-container">
          <span>ID: 4346</span>
          <span>Status: <span className="status failed">Failed</span></span>
          <span>Description: CheckSF2_True1</span>
          <span>Workflow Name: SECFIN</span>
        </div>
        <input type="text" className="comment-box" placeholder="Comment" />
        <button className="btn">Validate</button>
        <button className="btn">Save to DB</button>
      </div>
    </div>
  );
};

export default BBTView;
