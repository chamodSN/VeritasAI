
import React from 'react';
import { Gavel, GraduationCap, Calendar, Scale } from 'lucide-react';

export default function JudgeCard({ profile }) {
  if (!profile) return null;
  return (
    <div className="card mb-3">
      <div className="flex items-start gap-2.5 mb-3">
        <div className="w-8 h-8 rounded-full bg-sage-light flex items-center justify-center flex-shrink-0">
          <Gavel size={13} className="text-sage" />
        </div>
        <div>
          <h4 className="font-serif text-base font-semibold text-ink leading-tight">{profile.name}</h4>
          <p className="text-xs text-mist font-mono">{profile.court}</p>
        </div>
      </div>

      <div className="space-y-2 text-xs">
        {profile.appointing_president && (
          <Row icon={Scale} label="Appointed by" value={profile.appointing_president} />
        )}
        {profile.law_school && (
          <Row icon={GraduationCap} label="Law school" value={profile.law_school} />
        )}
        {profile.date_appointed && (
          <Row icon={Calendar} label="Appointed" value={profile.date_appointed.slice(0, 4)} />
        )}
        {profile.total_opinions > 0 && (
          <Row icon={Gavel} label="Opinions" value={profile.total_opinions.toLocaleString()} />
        )}
      </div>

      {profile.practice_areas?.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-3">
          {profile.practice_areas.map(a => (
            <span key={a} className="badge-neutral text-[10px]">{a}</span>
          ))}
        </div>
      )}
    </div>
  );
}

function Row({ icon: Icon, label, value }) {
  return (
    <div className="flex items-center gap-2">
      <Icon size={11} className="text-stone-dark flex-shrink-0" />
      <span className="text-mist">{label}:</span>
      <span className="text-ink font-medium">{value}</span>
    </div>
  );
}