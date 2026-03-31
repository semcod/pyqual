import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Repository } from '../types';

interface MetricsChartProps {
  repositories: Repository[];
}

const MetricsChart: React.FC<MetricsChartProps> = ({ repositories }) => {
  // Generate sample data for the chart
  const data = React.useMemo(() => {
    const days = 30;
    const today = new Date();
    const chartData = [];

    for (let i = days - 1; i >= 0; i--) {
      const date = new Date(today);
      date.setDate(date.getDate() - i);
      
      const dayData: any = {
        date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
      };

      // Add mock historical data for each repository
      repositories.forEach(repo => {
        if (repo.lastRun?.metrics.coverage) {
          // Simulate historical coverage with some variation
          const baseCoverage = repo.lastRun.metrics.coverage;
          const variation = (Math.random() - 0.5) * 10;
          dayData[repo.id] = Math.max(0, Math.min(100, baseCoverage + variation));
        }
      });

      chartData.push(dayData);
    }

    return chartData;
  }, [repositories]);

  const colors = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899'];

  return (
    <div className="h-80" style={{ height: '320px', width: '100%' }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis 
            dataKey="date" 
            interval={Math.floor(data.length / 10)}
            tick={{ fontSize: 12 }}
          />
          <YAxis 
            domain={[0, 100]}
            tick={{ fontSize: 12 }}
            label={{ value: 'Coverage %', angle: -90, position: 'insideLeft' }}
          />
          <Tooltip
            formatter={(value: number) => [`${value.toFixed(1)}%`, 'Coverage']}
            contentStyle={{
              backgroundColor: 'rgba(255, 255, 255, 0.95)',
              border: '1px solid #E5E7EB',
              borderRadius: '6px'
            }}
          />
          {repositories.map((repo, index) => (
            <Line
              key={repo.id}
              type="monotone"
              dataKey={repo.id}
              stroke={colors[index % colors.length]}
              strokeWidth={2}
              dot={false}
              name={repo.name}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default MetricsChart;
