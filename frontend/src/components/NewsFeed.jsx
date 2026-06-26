export default function NewsFeed({ news }) {
  const headlines = news?.headlines ?? [];
  if (!headlines.length) {
    return <div className="muted">Quiet day in the metropolis.</div>;
  }
  return (
    <ul className="news">
      {headlines.map((h, i) => <li key={i}>{h}</li>)}
    </ul>
  );
}
