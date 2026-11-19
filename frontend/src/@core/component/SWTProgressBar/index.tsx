"use client";

import { useEffect, useState } from "react";

interface SWTProgressBarProps {
  label: string;
}

export default function SWTProgressBar({ label }: SWTProgressBarProps) {
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => setSeconds((v) => v + 1), 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="progress" role="status">
      <div className="bar indeterminate">
        <div />
      </div>
      <span>
        {label}… {seconds}s
      </span>
    </div>
  );
}
