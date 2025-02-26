import React from "react";
import "./BBTDetailView.css";

interface BBTData {
  id: number;
  workflow: string;
  status: string;
  color: string;
  validated: boolean;
  description?: string;
  comment?: string;
}

interface BBTDetailViewProps {
  data: BBTData;
  onClose: () => void;
}

const BBTDetailView: React.FC<BBTDetailViewProps> = ({ data, onClose }) => {
  return (
    <div className="detail-view">
      <div className="header">
        <h2>BBT Detail View</h2>
        <button onClick={onClose} className="close-btn">X</button>
      </div>
      <p><strong>ID:</strong> {data.id}</p>
      <p><strong>Workflow:</strong> {data.workflow}</p>
      <p><strong>Status:</strong> <span className={data.color}>{data.status}</span></p>
      <p><strong>Description:</strong> {data.description || "N/A"}</p>
      <p><strong>Comment:</strong> {data.comment || "N/A"}</p>
      <button className="close-btn" onClick={onClose}>Close</button>
    </div>
  );
};

export default BBTDetailView;
