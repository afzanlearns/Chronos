import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:5000';

function StatCard({ title, value, icon, color }) {
  const colorClass = {
    blue: 'bg-blue-50 border-blue-200',
    green: 'bg-green-50 border-green-200',
    purple: 'bg-purple-50 border-purple-200',
    orange: 'bg-orange-50 border-orange-200'
  }[color] || 'bg-gray-50 border-gray-200';

  return (
    <div className={`${colorClass} border rounded-lg p-4`}>
      <div className="text-3xl mb-2">{icon}</div>
      <div className="text-sm text-gray-600">{title}</div>
      <div className="text-2xl font-bold">{value}</div>
    </div>
  );
}

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [appBreakdown, setAppBreakdown] = useState([]);
  const [tasks, setTasks] = useState([]);

  useEffect(() => {
    fetchDashboard();
    const interval = setInterval(fetchDashboard, 60000);
    return () => clearInterval(interval);
  }, []);

  const fetchDashboard = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/dashboard/today`);
      const data = await response.json();
      setStats(data.stats);
      setAppBreakdown(data.app_breakdown || []);
      setTasks(data.incomplete_tasks || []);
    } catch (err) {
      console.error('Dashboard fetch error:', err);
    }
  };

  if (!stats) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <p className="text-xl text-gray-500">Loading Chronos...</p>
      </div>
    );
  }

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">Today's Overview</h1>
        <div className="text-sm text-gray-500">
          {new Date().toLocaleDateString()}
        </div>
      </div>

      <div className="grid grid-cols-4 gap-4 mb-8">
        <StatCard
          title="Screen Time"
          value={`${Math.round(stats.total_screen_time_minutes)}m`}
          icon="🖥️"
          color="blue"
        />
        <StatCard
          title="Focus Time"
          value={`${Math.round(stats.focus_time_minutes)}m`}
          icon="⚡"
          color="green"
        />
        <StatCard
          title="Tasks Done"
          value={stats.tasks_completed}
          icon="✓"
          color="purple"
        />
        <StatCard
          title="Productivity"
          value={`${Math.round(stats.productivity_score)}/100`}
          icon="📈"
          color="orange"
        />
      </div>

      <div className="bg-white rounded-lg shadow p-6 mb-8">
        <h2 className="text-xl font-semibold mb-4">App Usage Breakdown</h2>
        {appBreakdown.length > 0 ? (
          <BarChart width={600} height={300} data={appBreakdown}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="app" />
            <YAxis />
            <Tooltip formatter={(val) => `${Math.round(val / 60)}m`} />
            <Bar dataKey="time_seconds" fill="#3b82f6" />
          </BarChart>
        ) : (
          <p className="text-gray-400">No app data yet. Start using apps to see breakdown.</p>
        )}
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Incomplete Tasks</h2>
        {tasks.length === 0 ? (
          <p className="text-gray-400">All tasks completed!</p>
        ) : (
          <ul className="space-y-2">
            {tasks.map((task) => (
              <li key={task.id} className="flex items-center p-3 bg-gray-50 rounded">
                <input type="checkbox" className="mr-3" />
                <span>{task.title}</span>
                <span className="ml-auto text-sm text-gray-500">
                  Due: {task.due ? new Date(task.due).toLocaleDateString() : 'No due date'}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
