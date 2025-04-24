'use client';

import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

interface Habit {
  name: string;
  completed: boolean;
}

// Custom Checkbox Component
const CustomCheckbox = ({ checked, onChange }: { checked: boolean; onChange: () => void }) => {
  return (
    <div
      onClick={onChange} // Make the whole area clickable
      className={`w-6 h-6 border-2 border-white rounded flex items-center justify-center cursor-pointer transition-colors duration-150 ease-in-out ${checked ? 'bg-white' : 'bg-black'}`}
    >
      {/* Checkmark (visible when checked) */}
      {checked && (
        <svg className="w-4 h-4 text-black" fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" viewBox="0 0 24 24" stroke="currentColor">
          <path d="M5 13l4 4L19 7"></path>
        </svg>
      )}
    </div>
  );
};

const API_BASE_URL = 'http://localhost:5001'; // Backend URL

export default function Menu() {
  const [habits, setHabits] = useState<Habit[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchHabits = useCallback(async () => {
    try {
      setLoading(true);
      const response = await axios.get<Habit[]>(`${API_BASE_URL}/habits`);
      setHabits(response.data);
      setError(null);
    } catch (err) {
      console.error("Error fetching habits:", err);
      setError("Failed to load habits. Ensure the backend is running.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHabits();
  }, [fetchHabits]);

  const toggleHabit = async (habitName: string) => {
    try {
      // Optimistic UI update
      setHabits(currentHabits =>
        currentHabits.map(habit =>
          habit.name === habitName ? { ...habit, completed: !habit.completed } : habit
        )
      );

      await axios.post(`${API_BASE_URL}/habits/${encodeURIComponent(habitName)}/toggle`);
    } catch (err) {
      console.error("Error toggling habit:", err);
      setError("Failed to update habit status.");
      // Revert optimistic update on error
      fetchHabits(); 
    }
  };

  // Render loading/error states with black background
  if (loading) {
    return <div className="min-h-screen bg-black text-white flex items-center justify-center text-center p-10">Loading Habits...</div>;
  }

  if (error) {
    return <div className="min-h-screen bg-black text-red-500 flex items-center justify-center text-center p-10">Error: {error}</div>;
  }

  return (
    <div className="min-h-screen bg-black text-white flex items-center justify-center p-4">
      {/* Changed bg-white to bg-black, text-black to text-white */}
      <div className="bg-black p-8 rounded-lg w-full max-w-md">
        {/* Changed title */}
        <h1 className="text-3xl font-bold mb-6 text-center">to do</h1>
        {/* Replaced table with divs */}
        <div className="space-y-4"> 
          {habits.map((habit, index) => (
            <div 
              key={habit.name} 
              // Added border-b, adjusted padding and layout
              className={`flex items-center justify-between p-4 border-b border-gray-700 ${index === habits.length - 1 ? 'border-b-0' : ''} ${habit.completed ? 'text-gray-500' : 'text-white'} transition-colors duration-150 ease-in-out`}
            >
              {/* Habit name, strike-through if completed */}
              <span className={`${habit.completed ? 'line-through' : ''}`}>{habit.name}</span>
              {/* Use CustomCheckbox */}
              <CustomCheckbox 
                checked={habit.completed}
                onChange={() => toggleHabit(habit.name)}
              />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
} 