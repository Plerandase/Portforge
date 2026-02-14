
import React from 'react';

interface CardProps {
  children: React.ReactNode;
  className?: string;
}

const Card: React.FC<CardProps> = ({ children, className = '' }) => {
  return (
    <div className={`bg-surface rounded-2xl shadow-sm overflow-hidden transition-all hover:shadow-xl hover:-translate-y-1 bg-white ${className}`}>
      {children}
    </div>
  );
};

export default Card;
