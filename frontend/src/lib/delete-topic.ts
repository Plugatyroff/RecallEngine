import { confirm } from '@/lib/confirm';
import { countDescendants, type TopicWithTotals } from '@/lib/topics';
import { api, type Topic } from '@/services/api';

/**
 * Ask for confirmation, then delete a topic with its subtopics and cards.
 * Resolves to true if it was deleted; throws ApiError if the server refused.
 */
export async function confirmAndDeleteTopic(topic: TopicWithTotals, allTopics: Topic[]): Promise<boolean> {
  const subtopics = countDescendants(allTopics, topic.id);
  const contents = [
    subtopics ? `${subtopics} subtopic${subtopics === 1 ? '' : 's'}` : null,
    `${topic.total_cards} card${topic.total_cards === 1 ? '' : 's'}`,
  ]
    .filter(Boolean)
    .join(' and ');
  const confirmed = await confirm(
    `Delete "${topic.name}"?`,
    `This deletes ${contents}, including their review history. It can't be undone.`,
    'Delete',
  );
  if (!confirmed) return false;
  await api.deleteTopic(topic.id);
  return true;
}
