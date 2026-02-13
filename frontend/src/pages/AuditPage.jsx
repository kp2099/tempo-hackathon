import { FileText, Shield } from 'lucide-react';
import AuditTrail from '../components/AuditTrail';

export default function AuditPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <FileText className="w-6 h-6 text-green-400" />
          On-Chain Audit Trail
        </h1>
        <p className="text-slate-400 mt-1">
          Tamper-proof record of every AI decision and payment — every entry is verifiable on Tempo blockchain
        </p>
      </div>

      {/* Explainer */}
      <div className="bg-green-900/10 border border-green-800/30 rounded-xl p-4 flex items-start gap-3">
        <Shield className="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0" />
        <div className="text-sm text-green-200">
          <p className="font-medium mb-1">Why On-Chain Audit?</p>
          <p className="text-green-300/70">
            Every expense decision by AgentFin is recorded with a programmable memo containing the
            risk score, category, and decision reason. These are immutably stored on the Tempo L1
            blockchain via TIP-20 transferWithMemo(), providing a tamper-proof audit trail that
            regulators and auditors can independently verify on explore.tempo.xyz.
          </p>
        </div>
      </div>

      <AuditTrail />
    </div>
  );
}

