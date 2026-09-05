import React, { useState, useEffect } from 'react';
import { History, Play, RotateCcw } from 'lucide-react';

const SLIDER_ANCHORS = [
  { position: 0, minutes: 1 },
  { position: 33, minutes: 60 },
  { position: 66, minutes: 1440 },
  { position: 100, minutes: 50400 },
];

const interpolate = (value, inMin, inMax, outMin, outMax) => {
  const progress = (value - inMin) / (inMax - inMin);
  return outMin + progress * (outMax - outMin);
};

const minutesFromSliderPosition = (position) => {
  for (let i = 1; i < SLIDER_ANCHORS.length; i += 1) {
    const prev = SLIDER_ANCHORS[i - 1];
    const next = SLIDER_ANCHORS[i];
    if (position <= next.position) {
      return Math.round(interpolate(position, prev.position, next.position, prev.minutes, next.minutes));
    }
  }

  return SLIDER_ANCHORS[SLIDER_ANCHORS.length - 1].minutes;
};

const sliderPositionFromMinutes = (minutes) => {
  for (let i = 1; i < SLIDER_ANCHORS.length; i += 1) {
    const prev = SLIDER_ANCHORS[i - 1];
    const next = SLIDER_ANCHORS[i];
    if (minutes <= next.minutes) {
      return Math.round(interpolate(minutes, prev.minutes, next.minutes, prev.position, next.position));
    }
  }

  return SLIDER_ANCHORS[SLIDER_ANCHORS.length - 1].position;
};

export function TimeTravelBar({ asOf, setAsOf, onResetSession, serverTime }) {
  const [minutesOffset, setMinutesOffset] = useState(60);
  const [sliderPosition, setSliderPosition] = useState(sliderPositionFromMinutes(60));

  useEffect(() => {
    if (asOf && serverTime) {
      const diffMin = Math.round(Math.max(1, (serverTime - asOf) / 60));
      setMinutesOffset(diffMin);
      setSliderPosition(sliderPositionFromMinutes(diffMin));
    }
  }, [asOf, serverTime]);

  const presets = [
    { label: '15m', minutes: 15 },
    { label: '1h', minutes: 60 },
    { label: '4h', minutes: 240 },
    { label: '1d', minutes: 1440 },
    { label: '35d (Long Absence)', minutes: 50400 },
  ];

  const handleSliderChange = (e) => {
    const position = Number(e.target.value);
    const val = minutesFromSliderPosition(position);
    setSliderPosition(position);
    setMinutesOffset(val);
    if (serverTime) {
      setAsOf(serverTime - (val * 60));
    }
  };

  const handlePresetSelect = (minutes) => {
    setMinutesOffset(minutes);
    setSliderPosition(sliderPositionFromMinutes(minutes));
    if (serverTime) {
      setAsOf(serverTime - (minutes * 60));
    }
  };

  const formatOffsetLabel = (min) => {
    if (min < 60) return `${min} minutes ago`;
    if (min < 1440) return `${(min / 60).toFixed(1)} hours ago`;
    return `${(min / 1440).toFixed(1)} days ago`;
  };

  return (
    <div className="glass-panel rounded-2xl p-4 md:p-5 mb-6 shadow-lg border border-slate-800">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <History className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-200">Time Travel Debugger</h3>
            <p className="text-xs text-slate-400 font-mono">
              Baseline `as_of`: <span className="text-indigo-400 font-medium">{formatOffsetLabel(minutesOffset)}</span>
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {presets.map(p => {
            const isActive = Math.abs(minutesOffset - p.minutes) < 5;
            return (
              <button
                key={p.label}
                onClick={() => handlePresetSelect(p.minutes)}
                className={`px-3 py-1.5 rounded-xl text-xs font-mono font-medium transition-all ${
                  isActive
                    ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30 border border-indigo-400'
                    : 'bg-slate-800/90 text-slate-300 hover:bg-slate-700/90 border border-slate-700/80'
                }`}
              >
                {p.label}
              </button>
            );
          })}

          <button
            onClick={() => {
              setMinutesOffset(0);
              setSliderPosition(0);
              onResetSession();
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/25 transition-all"
            title="Update last_viewed_at to current timestamp"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset to Now</span>
          </button>
        </div>
      </div>

      <div className="mt-4 pt-3 border-t border-slate-800/80">
        <div className="flex items-center justify-between text-xs text-slate-400 font-mono mb-1.5">
          <span>1 min</span>
          <span>1 hour</span>
          <span>1 day</span>
          <span className="text-purple-400 font-semibold">35 days (&gt;30d Fallback)</span>
        </div>
        <input
          type="range"
          min="0"
          max="100"
          step="1"
          value={sliderPosition}
          onChange={handleSliderChange}
          className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500 hover:accent-indigo-400"
        />
      </div>
    </div>
  );
}
