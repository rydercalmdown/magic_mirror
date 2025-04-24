'use client';

import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

interface Habit {
  name: string;
  completed: boolean;
}

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
      // Optionally re-fetch habits to confirm, or rely on optimistic update
      // fetchHabits(); 
    } catch (err) {
      console.error("Error toggling habit:", err);
      setError("Failed to update habit status.");
      // Revert optimistic update on error
      fetchHabits(); 
    }
  };

  if (loading) {
    return <div className="text-white text-center p-10">Loading Habits...</div>;
  }

  if (error) {
    return <div className="text-red-500 text-center p-10">Error: {error}</div>;
  }

  return (
    <div className="min-h-screen bg-black flex items-center justify-center">
      <div className="bg-white text-black p-8 rounded-lg shadow-lg w-full max-w-md">
        <h1 className="text-3xl font-bold mb-6 text-center">Today's Habits</h1>
        <table className="w-full table-auto border-collapse">
          <thead>
            <tr className="bg-gray-200">
              <th className="border px-4 py-2 text-left">Habit</th>
              <th className="border px-4 py-2 text-center">Completed?</th>
            </tr>
          </thead>
          <tbody>
            {habits.map((habit) => (
              <tr key={habit.name} className="hover:bg-gray-100">
                <td className="border px-4 py-2">{habit.name}</td>
                <td className="border px-4 py-2 text-center">
                  <input
                    type="checkbox"
                    checked={habit.completed}
                    onChange={() => toggleHabit(habit.name)}
                    className="form-checkbox h-5 w-5 text-blue-600 cursor-pointer"
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
} 