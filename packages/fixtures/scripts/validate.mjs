import { readFile } from 'node:fs/promises';

const root = new URL('../', import.meta.url);
const scenarioFiles = ['users.json', 'repositories.json', 'collaboration.json', 'failures.json'];
const failures = [];
const readJson = async (name) => JSON.parse(await readFile(new URL(`scenarios/${name}`, root), 'utf8'));
for (const name of scenarioFiles) {
  const scenario = await readJson(name);
  if (!scenario.scenario || !scenario.asOf) failures.push(`${name}: scenario and asOf are required`);
  if (scenario.asOf !== '2026-01-15T12:00:00Z') failures.push(`${name}: asOf must remain deterministic`);
}
const users = await readJson('users.json');
const repositories = await readJson('repositories.json');
const userIds = new Set(users.items.map((user) => user.id));
for (const repository of repositories.items) {
  if (!userIds.has(repository.owner.id)) failures.push(`repositories.json: unknown owner ${repository.owner.id}`);
}
const failuresScenario = await readJson('failures.json');
for (const item of failuresScenario.cases) {
  if (item.status !== item.problem.status) failures.push(`failures.json: ${item.name} status mismatch`);
  if (!item.problem.code) failures.push(`failures.json: ${item.name} has no stable problem code`);
}
if (failures.length) {
  console.error(failures.join('\n'));
  process.exit(1);
}
console.log(`Validated ${scenarioFiles.length} deterministic fixture scenarios.`);
