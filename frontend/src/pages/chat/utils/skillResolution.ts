import { Agent, SkillSpec, VisibleSkillChip } from '../../../types';
import { getAgentVisibleSkills } from '../../../hooks/useChatState';

const versionKey = (value: string) =>
  value.split(/(\d+)/).map((token) => (token.match(/^\d+$/) ? Number(token) : token));

export const compareVersion = (a: string, b: string) => {
  const ka = versionKey(a);
  const kb = versionKey(b);
  const len = Math.max(ka.length, kb.length);

  for (let i = 0; i < len; i += 1) {
    const va = ka[i];
    const vb = kb[i];
    if (va === undefined) return -1;
    if (vb === undefined) return 1;
    if (typeof va === 'number' && typeof vb === 'number') {
      if (va !== vb) return va > vb ? 1 : -1;
    } else if (String(va) !== String(vb)) {
      return String(va) > String(vb) ? 1 : -1;
    }
  }

  return 0;
};

export const resolveSkillSpec = (skills: SkillSpec[], nameVersion: string) => {
  if (nameVersion.includes(':')) {
    const [name, version] = nameVersion.split(':', 2);
    return skills.find((skill) => skill.name === name && skill.version === version);
  }

  const matches = skills.filter((skill) => skill.name === nameVersion);
  if (matches.length === 0) return undefined;
  return [...matches].sort((a, b) => compareVersion(a.version, b.version)).pop();
};

export const parseSkillReference = (skillId: string) => {
  if (!skillId.includes(':')) {
    return { name: skillId, version: undefined as string | undefined };
  }
  const [name, version] = skillId.split(':', 2);
  return { name, version };
};

export const buildVisibleSkillOptions = (
  skills: SkillSpec[],
  agent?: Agent | null,
): VisibleSkillChip[] => {
  const visibleSkillIds = getAgentVisibleSkills(agent);

  return visibleSkillIds.flatMap((skillId) => {
    const spec = resolveSkillSpec(skills, skillId);
    if (spec?.availability === false) return [];
    if (spec) {
      return [{ id: skillId, name: spec.name, version: spec.version }];
    }
    const parsed = parseSkillReference(skillId);
    return [{ id: skillId, name: parsed.name, version: parsed.version }];
  });
};
