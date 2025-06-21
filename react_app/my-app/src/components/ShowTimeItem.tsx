import type { FC } from 'react';

export interface ShowTime {
  id: string;
  cinema: string;
  title: string;
  link: string;
  datetime: string;
  description: string;
  image_src: string;
  last_updated: string;
  scraper: string;
}

interface Props {
  showtime: ShowTime;
}

const ShowTimeItem: FC<Props> = ({ showtime }) => {
  const timeString = new Date(showtime.datetime).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  });

  return (
    <a
      href={showtime.link}
      target="_blank"
      rel="noopener noreferrer"
      style={{
        display: 'block',
        padding: '0.5rem 0',
        borderBottom: '1px solid #ddd',
        textDecoration: 'none',
        color: '#000',
      }}
    >
      <div style={{ fontWeight: 'bold', fontSize: '0.95rem' }}>
        {showtime.title} &middot; {showtime.cinema} &middot; {timeString}
      </div>
      <div style={{ fontSize: '0.8rem', color: '#444', marginTop: '0.25rem' }}>
        {showtime.description.length > 100
          ? showtime.description.slice(0, 250) + '...'
          : showtime.description}
      </div>
    </a>
  );
};

export default ShowTimeItem;
