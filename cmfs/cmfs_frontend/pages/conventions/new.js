import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import useAuth from '../../lib/useAuth';
import { createConvention, listCounties, listRegions } from '../../lib/conventions';

const STEPS = ['Details', 'Scope', 'Participants', 'Confirm'];

export default function NewConventionPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [step, setStep] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  // Step 1 fields
  const [name, setName] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [description, setDescription] = useState('');
  const [feeStudent, setFeeStudent] = useState('');
  const [feeKessat, setFeeKessat] = useState('');
  const [feeAssociate, setFeeAssociate] = useState('');

  // Step 2
  const [scope, setScope] = useState('county');

  // Step 3
  const [counties, setCounties] = useState([]);
  const [regions, setRegions] = useState([]);
  const [units, setUnits] = useState([]);

  // Redirect non-super-admins
  useEffect(() => {
    if (!authLoading && user && user.role !== 'super_admin') {
      router.replace('/conventions');
    }
  }, [user, authLoading]);

  async function loadGeography() {
    const [cRes, rRes] = await Promise.all([listCounties(), listRegions()]);
    if (cRes.ok) setCounties(cRes.data.counties || []);
    if (rRes.ok) setRegions(rRes.data.regions || []);
  }

  function validateStep0() {
    if (!name.trim()) return 'Convention name is required.';
    if (!startDate) return 'Start date is required.';
    if (!endDate) return 'End date is required.';
    if (startDate >= endDate) return 'End date must be after start date.';
    if (!feeStudent || Number(feeStudent) < 0) return 'Valid student fee is required.';
    if (!feeKessat || Number(feeKessat) < 0) return 'Valid Kessat fee is required.';
    if (!feeAssociate || Number(feeAssociate) < 0) return 'Valid associate fee is required.';
    return null;
  }

  async function goNext() {
    setError('');
    if (step === 0) {
      const err = validateStep0();
      if (err) { setError(err); return; }
    }
    if (step === 1) {
      setUnits([]);
      await loadGeography();
    }
    setStep(s => s + 1);
  }

  function toggleUnit(id, name) {
    setUnits(prev => prev.find(u => u.scope_id === id)
      ? prev.filter(u => u.scope_id !== id)
      : [...prev, { scope_id: id, display_name: name }]
    );
  }

  async function handleSubmit() {
    setError('');
    if (scope !== 'national' && units.length === 0) {
      setError('Select at least one participating unit.');
      return;
    }
    setSubmitting(true);
    try {
      const res = await createConvention({
        name: name.trim(), start_date: startDate, end_date: endDate,
        description: description.trim(), scope,
        fee_student: parseFloat(feeStudent),
        fee_kessat: parseFloat(feeKessat),
        fee_associate: parseFloat(feeAssociate),
        units: scope === 'national'
          ? [{ scope_id: null }]
          : units.map(u => ({ scope_id: u.scope_id })),
      });
      if (!res.ok) throw new Error(res.data?.error || 'Failed to create convention.');
      router.push(`/conventions/${res.data.convention.id}`);
    } catch (err) {
      setError(typeof err.message === 'object' ? JSON.stringify(err.message) : err.message);
    } finally {
      setSubmitting(false);
    }
  }

  if (authLoading || !user) return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
    </div>
  );

  const scopeItems = scope === 'county' ? counties : regions;

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center gap-3 mb-3">
          <Link href="/conventions" className="text-gray-400 hover:text-gray-600 text-sm">← Conventions</Link>
          <span className="text-gray-300">/</span>
          <span className="text-gray-700 font-medium">New Convention</span>
        </div>
        {/* Step indicators */}
        <div className="flex items-center gap-2">
          {STEPS.map((label, i) => (
            <div key={i} className="flex items-center gap-2">
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${
                i < step ? 'bg-green-500 text-white' : i === step ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-500'
              }`}>{i < step ? '✓' : i + 1}</div>
              <span className={`text-sm ${i === step ? 'font-medium text-gray-900' : 'text-gray-400'}`}>{label}</span>
              {i < STEPS.length - 1 && <div className="w-6 h-px bg-gray-300" />}
            </div>
          ))}
        </div>
      </div>

      <div className="max-w-xl mx-auto px-6 py-8">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 mb-5 text-sm">{error}</div>
        )}

        {/* Step 0: Details */}
        {step === 0 && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 space-y-5">
            <h2 className="text-lg font-semibold text-gray-800">Convention Details</h2>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
              <input type="text" value={name} onChange={e => setName(e.target.value)}
                placeholder="e.g. KSCF April Convention 2025"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Start Date *</label>
                <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">End Date *</label>
                <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
              <textarea rows={3} value={description} onChange={e => setDescription(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-700 mb-3">Registration Fees (KES) *</p>
              <div className="grid grid-cols-3 gap-3">
                {[['Student', feeStudent, setFeeStudent], ['Kessat', feeKessat, setFeeKessat], ['Associate', feeAssociate, setFeeAssociate]].map(([label, val, setter]) => (
                  <div key={label}>
                    <label className="block text-xs text-gray-500 mb-1">{label}</label>
                    <input type="number" min="0" step="50" value={val} onChange={e => setter(e.target.value)}
                      placeholder="0"
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 text-right focus:outline-none focus:ring-2 focus:ring-blue-500" />
                  </div>
                ))}
              </div>
            </div>
            <div className="flex justify-end pt-2">
              <button onClick={goNext} className="bg-blue-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-blue-700">
                Next: Scope →
              </button>
            </div>
          </div>
        )}

        {/* Step 1: Scope */}
        {step === 1 && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-5">Select Scope</h2>
            <div className="space-y-3">
              {[
                { value: 'county', label: 'County', desc: 'One unit per participating county.' },
                { value: 'regional', label: 'Regional', desc: 'One unit per participating region.' },
                { value: 'national', label: 'National', desc: 'Single national convention unit.' },
              ].map(opt => (
                <label key={opt.value} className={`flex items-start gap-4 p-4 border rounded-lg cursor-pointer transition ${
                  scope === opt.value ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'
                }`}>
                  <input type="radio" name="scope" value={opt.value} checked={scope === opt.value}
                    onChange={() => setScope(opt.value)} className="mt-1 accent-blue-600" />
                  <div>
                    <p className="font-medium text-gray-900">{opt.label}</p>
                    <p className="text-sm text-gray-500">{opt.desc}</p>
                  </div>
                </label>
              ))}
            </div>
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg px-4 py-3 mt-4 text-sm text-yellow-800">
              ⚠️ Scope and fees are <strong>permanently locked</strong> once published.
            </div>
            <div className="flex justify-between mt-6">
              <button onClick={() => setStep(0)} className="border border-gray-300 text-gray-700 px-5 py-2 rounded-lg hover:bg-gray-50">← Back</button>
              <button onClick={goNext} className="bg-blue-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-blue-700">Next: Participants →</button>
            </div>
          </div>
        )}

        {/* Step 2: Participants */}
        {step === 2 && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-1">Assign Participants</h2>
            <p className="text-sm text-gray-500 mb-4">
              {scope === 'national' ? 'A single national unit will be created automatically.' : `Select participating ${scope === 'county' ? 'counties' : 'regions'}.`}
            </p>
            {scope === 'national' ? (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm text-blue-700">
                ✓ National unit will be created automatically.
              </div>
            ) : (
              <div className="border border-gray-200 rounded-lg divide-y divide-gray-100 max-h-72 overflow-y-auto mb-4">
                {scopeItems.length === 0 ? (
                  <p className="text-sm text-gray-400 p-4">Loading…</p>
                ) : scopeItems.map(item => {
                  const selected = units.find(u => u.scope_id === item.id);
                  return (
                    <div key={item.id} onClick={() => toggleUnit(item.id, item.name)}
                      className={`flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-gray-50 ${selected ? 'bg-blue-50' : ''}`}>
                      <input type="checkbox" readOnly checked={!!selected} className="accent-blue-600 pointer-events-none" />
                      <span className="text-sm text-gray-800">{item.name}</span>
                      {item.county_code && <span className="text-xs text-gray-400 font-mono ml-auto">{item.county_code}</span>}
                    </div>
                  );
                })}
              </div>
            )}
            <div className="flex justify-between mt-6">
              <button onClick={() => setStep(1)} className="border border-gray-300 text-gray-700 px-5 py-2 rounded-lg hover:bg-gray-50">← Back</button>
              <button onClick={() => { setError(''); setStep(3); }} className="bg-blue-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-blue-700">Review →</button>
            </div>
          </div>
        )}

        {/* Step 3: Confirm */}
        {step === 3 && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-5">Confirm & Create</h2>
            <dl className="space-y-2 text-sm mb-5">
              {[
                ['Name', name], ['Scope', scope], ['Dates', `${startDate} → ${endDate}`],
                ['Student Fee', `KES ${Number(feeStudent).toLocaleString()}`],
                ['Kessat Fee', `KES ${Number(feeKessat).toLocaleString()}`],
                ['Associate Fee', `KES ${Number(feeAssociate).toLocaleString()}`],
                ['Units', scope === 'national' ? '1 (National)' : `${units.length} selected`],
              ].map(([label, val]) => (
                <div key={label} className="flex">
                  <dt className="w-36 text-gray-500 shrink-0">{label}</dt>
                  <dd className="text-gray-900 font-medium capitalize">{val}</dd>
                </div>
              ))}
            </dl>
            <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 text-sm text-blue-700 mb-5">
              Convention will be created in <strong>Draft</strong> status. You can edit before publishing.
            </div>
            <div className="flex justify-between">
              <button onClick={() => setStep(2)} className="border border-gray-300 text-gray-700 px-5 py-2 rounded-lg hover:bg-gray-50">← Back</button>
              <button onClick={handleSubmit} disabled={submitting}
                className="bg-green-600 text-white px-6 py-2 rounded-lg font-semibold hover:bg-green-700 disabled:opacity-50">
                {submitting ? 'Creating…' : '✓ Create Convention'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}