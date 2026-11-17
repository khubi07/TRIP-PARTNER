import type { TripContext } from '../types';

function TripTag({ children }: { children: string }) {
  return <span className="tag">{children}</span>;
}

export default function TripSidebar({ context }: { context: TripContext | null }) {
  const formatDate = (value: string) => new Date(`${value}T12:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  const year = context ? new Date(`${context.check_in}T12:00:00`).getFullYear() : '';

  return (
    <aside className="sidebar">
      <a className="brand" href="/" aria-label="tripPartner home">
        <span className="brand-mark">t<span>p</span></span>
        <span>tripPartner<small>MEGHALAYA, MADE PERSONAL</small></span>
      </a>
      <div className="trip-label">YOUR ACTIVE TRIP</div>
      <section className="trip-card" aria-label="Trip details">
        <div className="trip-image"><span className="image-caption">THE ABODE OF CLOUDS</span><span className="image-badge">● UPCOMING</span></div>
        <div className="trip-card-body">
          <div className="eyebrow">MEGHALAYA · 3 NIGHTS</div>
          <h1>{context?.property.name ?? 'Loading your stay…'}</h1>
          <p className="trip-dates">{context ? `${formatDate(context.check_in)} — ${formatDate(context.check_out)}, ${year}` : 'Checking trip details'}</p>
          <div className="stay-line"><span className="stay-dot" /><span>{context?.property.area ?? 'Sohra, Meghalaya'}</span></div>
        </div>
      </section>
      <div className="section-heading"><span>YOUR TRIP PROFILE</span><span className="edit-label">FROM YOUR BOOKING</span></div>
      <section className="profile-card">
        <div className="profile-row"><span className="profile-icon">✦</span><div><small>TRAVELLING</small><strong>{context ? `${context.guest_count} guests` : '—'}</strong></div></div>
        <div className="profile-row"><span className="profile-icon">♡</span><div><small>YOU'RE INTO</small><div className="tag-list">{context?.preferences.interests.map(value => <TripTag key={value}>{value}</TripTag>)}</div></div></div>
        <div className="profile-row"><span className="profile-icon">⌂</span><div><small>YOUR VIBE</small><div className="tag-list">{context?.preferences.preferred_vibe.map(value => <TripTag key={value}>{value}</TripTag>)}</div></div></div>
      </section>
      <div className="sidebar-foot"><span className="pulse-dot" /> Your concierge is ready <span className="demo-pill">DEMO TRIP</span></div>
    </aside>
  );
}
