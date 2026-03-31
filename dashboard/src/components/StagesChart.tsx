import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { PyqualStage } from '../types';

interface StagesChartProps {
  stages: PyqualStage[];
}

const StagesChart: React.FC<StagesChartProps> = ({ stages }) => {
  const data = stages.map(stage => ({
    name: stage.name,
    duration: stage.duration_s,
    passed: stage.passed ? 1 : 0,
    skipped: stage.skipped ? 1 : 0
  }));

  return (
    <div className="h-64" style={{ height: '256px', width: '100%' }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis 
            dataKey="name" 
            tick={{ fontSize: 12 }}
            angle={-45}
            textAnchor="end"
            height={60}
          />
          <YAxis 
            tick={{ fontSize: 12 }}
            label={{ value: 'Duration (s)', angle: -90, position: 'insideLeft' }}
          />
          <Tooltip
            formatter={(value: number, name: string) => {
              if (name === 'duration') return [`${value.toFixed(2)}s`, 'Duration'];
              return [value, name];
            }}
            contentStyle={{
              backgroundColor: 'rgba(255, 255, 255, 0.95)',
              border: '1px solid #E5E7EB',
              borderRadius: '6px'
            }}
          />
          <Bar 
            dataKey="duration" 
            fill="#3B82F6"
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

export default StagesChart;
