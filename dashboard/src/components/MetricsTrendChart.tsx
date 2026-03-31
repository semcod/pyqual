import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { PyqualSummary } from '../types';

interface MetricsTrendChartProps {
  runs: PyqualSummary[];
}

const MetricsTrendChart: React.FC<MetricsTrendChartProps> = ({ runs }) => {
  const data = React.useMemo(() => {
    return runs.map(run => ({
      date: new Date(run.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      coverage: run.metrics.coverage || 0,
      maintainability: run.metrics.maintainability || 0,
      security: run.metrics.security || 0,
      reliability: run.metrics.reliability || 0
    }));
  }, [runs]);

  if (runs.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-gray-500">
        No historical data available
      </div>
    );
  }

  return (
    <div className="h-64" style={{ height: '256px', width: '100%' }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis 
            dataKey="date" 
            tick={{ fontSize: 12 }}
          />
          <YAxis 
            domain={[0, 100]}
            tick={{ fontSize: 12 }}
            label={{ value: 'Score %', angle: -90, position: 'insideLeft' }}
          />
          <Tooltip
            formatter={(value: number) => [`${value.toFixed(1)}%`, '']}
            contentStyle={{
              backgroundColor: 'rgba(255, 255, 255, 0.95)',
              border: '1px solid #E5E7EB',
              borderRadius: '6px'
            }}
          />
          <Line type="monotone" dataKey="coverage" stroke="#3B82F6" strokeWidth={2} />
          <Line type="monotone" dataKey="maintainability" stroke="#10B981" strokeWidth={2} />
          <Line type="monotone" dataKey="security" stroke="#F59E0B" strokeWidth={2} />
          <Line type="monotone" dataKey="reliability" stroke="#8B5CF6" strokeWidth={2} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default MetricsTrendChart;
