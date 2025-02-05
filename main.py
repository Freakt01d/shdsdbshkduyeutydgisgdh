import React, { useState } from "react";

const BBTAnalyzer = () => {
  const initialRows = [
    { id: 4198, workflow: "COLLAT", status: "Passed", color: "bg-green-500", validated: false },
    { id: 4199, workflow: "MIFID-1", status: "Passed", color: "bg-green-500", validated: false },
    { id: 4200, workflow: "DFA", status: "False", color: "bg-red-500", validated: false },
    { id: 4201, workflow: "COLLAT", status: "False", color: "bg-red-500", validated: false },
    { id: 4202, workflow: "IFU", status: "Passed", color: "bg-green-500", validated: false },
    { id: 4203, workflow: "DFA", status: "Passed", color: "bg-green-500", validated: false },
    { id: 4204, workflow: "FATCA_ETNC", status: "Passed", color: "bg-green-500", validated: false },
    { id: 4205, workflow: "DFA", status: "Passed", color: "bg-green-500", validated: false },
    { id: 4206, workflow: "COLLAT", status: "Passed", color: "bg-green-500", validated: false },
    { id: 4207, workflow: "MIFID-1", status: "Passed", color: "bg-green-500", validated: false },
  ];

  const [showTable, setShowTable] = useState(false);
  const [rows, setRows] = useState(initialRows);

  const handleValidate = (index) => {
    setRows((prevRows) =>
      prevRows.map((row, i) =>
        i === index
          ? {
              ...row,
              validated: !row.validated,
              status: !row.validated ? "Validated" : initialRows.find(r => r.id === row.id)?.status || "Passed",
              color: !row.validated ? "bg-yellow-500" : (initialRows.find(r => r.id === row.id)?.color || "bg-green-500"),
            }
          : row
      )
    );
  };

  const totalCount = rows.length;
  const validatedCount = rows.filter(row => row.validated).length;
  const passedCount = rows.filter(row => row.status === "Passed" || row.status === "Validated" && initialRows.find(r => r.id === row.id)?.status === "Passed").length;
  const failedCount = rows.filter(row => row.status === "False" || row.status === "Validated" && initialRows.find(r => r.id === row.id)?.status === "False").length;

  return (
    <div className="p-4 bg-gray-100 h-screen">
      <div className="flex items-center space-x-2 mb-4">
        <select className="border p-2 rounded">
          <option>ISO_25.01.31.1</option>
        </select>
        <button className="bg-blue-500 text-white px-4 py-2 rounded" onClick={() => setShowTable(true)}>
          Start Comparison
        </button>
        <button className="bg-gray-500 text-white px-4 py-2 rounded">View Report</button>
        <button className="bg-gray-500 text-white px-4 py-2 rounded">Email Report</button>
        <div className="w-8"></div>
        <button className="bg-gray-500 text-white px-4 py-2 rounded">Initiate New BBT</button>
        <button className="bg-gray-500 text-white px-4 py-2 rounded">Add BBT</button>
      </div>

      {showTable && (
        <div className="bg-white p-4 rounded shadow-md overflow-auto">
          <table className="w-full border-collapse border text-left">
            <thead>
              <tr className="bg-gray-200">
                <th className="border p-2">ID</th>
                <th className="border p-2">Workflow</th>
                <th className="border p-2">Is Active</th>
                <th className="border p-2">Status</th>
                <th className="border p-2">View</th>
                <th className="border p-2">Validate</th>
                <th className="border p-2">Description</th>
                <th className="border p-2">Comment</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={row.id} className="border">
                  <td className="border p-2">{row.id}</td>
                  <td className="border p-2">{row.workflow}</td>
                  <td className="border p-2"><input type="checkbox" checked readOnly /></td>
                  <td className={`border p-2 ${row.color} text-white`}>{row.status}</td>
                  <td className="border p-2"><button className="bg-gray-300 px-2 py-1 rounded">View</button></td>
                  <td className="border p-2">
                    <input type="checkbox" checked={row.validated} onChange={() => handleValidate(index)} />
                  </td>
                  <td className="border p-2">Description here</td>
                  <td className="border p-2">Comment here</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="mt-4 flex justify-between">
        <div className="w-1/4 bg-white p-4 rounded shadow-md">
          <h3 className="font-bold">Filter</h3>
          <div>
            <label><input type="checkbox" /> Passed</label><br/>
            <label><input type="checkbox" /> Failed</label><br/>
            <label><input type="checkbox" /> Validated</label>
          </div>
        </div>

        <div className="w-1/4 bg-white p-4 rounded shadow-md">
          <h3 className="font-bold">Statistics</h3>
          <p>Total Count: {totalCount}</p>
          <p>Passed Count: {passedCount}</p>
          <p>Failed Count: {failedCount}</p>
          <p>Validated Count: {validatedCount}</p>
          <p>Executed on: 1/31/2025 9:43 AM</p>
          <button className="bg-blue-500 text-white px-4 py-2 rounded w-full mt-2">Update Active Flag to DB</button>
          <button className="bg-gray-500 text-white px-4 py-2 rounded w-full mt-2">Save and Export Report</button>
        </div>
      </div>
    </div>
  );
};

export default BBTAnalyzer;
