import { useState, useEffect } from 'react';
import { Users, ChevronDown, ChevronRight, User, Shield, Wallet, Building2 } from 'lucide-react';
import { getOrgTree } from '../api/client';

const roleColors = {
  employee: 'bg-blue-500/10 text-blue-400 ring-blue-500/20',
  manager: 'bg-green-500/10 text-green-400 ring-green-500/20',
  finance: 'bg-yellow-500/10 text-yellow-400 ring-yellow-500/20',
  vp: 'bg-purple-500/10 text-purple-400 ring-purple-500/20',
  cfo: 'bg-red-500/10 text-red-400 ring-red-500/20',
  director: 'bg-orange-500/10 text-orange-400 ring-orange-500/20',
};

function OrgNode({ node, depth = 0 }) {
  const [expanded, setExpanded] = useState(depth < 2);
  const hasChildren = node.direct_reports && node.direct_reports.length > 0;
  const rc = roleColors[node.role] || roleColors.employee;

  return (
    <div className="select-none">
      <div
        className={`flex items-center gap-2 py-2 px-3 rounded-lg hover:bg-slate-700/50 transition-colors cursor-pointer ${
          depth === 0 ? 'bg-slate-700/30' : ''
        }`}
        style={{ marginLeft: depth * 24 }}
        onClick={() => hasChildren && setExpanded(!expanded)}
      >
        {hasChildren ? (
          expanded ? (
            <ChevronDown className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
          ) : (
            <ChevronRight className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
          )
        ) : (
          <span className="w-3.5 flex-shrink-0" />
        )}

        <User className="w-4 h-4 text-slate-400 flex-shrink-0" />

        <div className="flex-1 min-w-0">
          <span className="text-sm font-medium text-white">{node.name}</span>
          <span className="text-xs text-slate-500 ml-2">{node.employee_id}</span>
        </div>

        <span className={`text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded ring-1 ${rc}`}>
          {node.role}
        </span>

        <span className="text-xs text-slate-500 flex items-center gap-1">
          <Building2 className="w-3 h-3" />
          {node.department}
        </span>
      </div>

      {expanded && hasChildren && (
        <div className="border-l border-slate-700/50" style={{ marginLeft: depth * 24 + 12 }}>
          {node.direct_reports.map((child) => (
            <OrgNode key={child.employee_id} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function OrgChart() {
  const [orgTree, setOrgTree] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadOrg();
  }, []);

  const loadOrg = async () => {
    try {
      const res = await getOrgTree();
      setOrgTree(res.data.org_tree || []);
    } catch (err) {
      console.error('Failed to load org tree:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-2">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-8 bg-slate-700 rounded animate-pulse" style={{ marginLeft: i * 24 }} />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-1">
      <div className="flex items-center gap-2 mb-3">
        <Users className="w-5 h-5 text-purple-400" />
        <h3 className="text-sm font-semibold text-white">Organization Hierarchy</h3>
      </div>

      {orgTree.length === 0 ? (
        <p className="text-slate-500 text-sm text-center py-8">No org data available</p>
      ) : (
        orgTree.map((root) => (
          <OrgNode key={root.employee_id} node={root} depth={0} />
        ))
      )}

      {/* Legend */}
      <div className="flex flex-wrap gap-2 mt-4 pt-3 border-t border-slate-700">
        {Object.entries(roleColors).map(([role, classes]) => (
          <span key={role} className={`text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded ring-1 ${classes}`}>
            {role}
          </span>
        ))}
      </div>
    </div>
  );
}
