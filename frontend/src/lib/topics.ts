import type { Topic } from '@/services/api';

export type TopicWithTotals = Topic & {
  /** Cards in this topic and all its subtopics */
  total_cards: number;
  total_due: number;
};

/** Add subtree totals to each topic. The API sends counts for each topic on its own. */
export function withTotals(topics: Topic[]): TopicWithTotals[] {
  const children = new Map<number | null, Topic[]>();
  for (const topic of topics) {
    children.set(topic.parent_id, [...(children.get(topic.parent_id) ?? []), topic]);
  }
  const totals = new Map<number, { cards: number; due: number }>();
  const total = (topic: Topic): { cards: number; due: number } => {
    const cached = totals.get(topic.id);
    if (cached) return cached;
    let cards = topic.card_count;
    let due = topic.due_count;
    for (const child of children.get(topic.id) ?? []) {
      const sub = total(child);
      cards += sub.cards;
      due += sub.due;
    }
    const result = { cards, due };
    totals.set(topic.id, result);
    return result;
  };
  return topics.map((topic) => ({
    ...topic,
    total_cards: total(topic).cards,
    total_due: total(topic).due,
  }));
}
