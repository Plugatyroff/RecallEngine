import { router } from 'expo-router';
import { useState } from 'react';
import { View } from 'react-native';

import { Button, Input, Label, Row, SectionTitle } from '@/components/ui';
import { Spacing } from '@/constants/theme';
import { showMenu } from '@/lib/confirm';
import { confirmAndDeleteTopic } from '@/lib/delete-topic';
import type { TopicWithTotals } from '@/lib/topics';
import { api, ApiError } from '@/services/api';

/**
 * The subtopics of one topic (or the top-level topics), plus a field to add a new one.
 * Tap a topic to open it; long-press it for a menu (delete).
 */
export function TopicList({
  topics,
  parentId,
  onChanged,
}: {
  topics: TopicWithTotals[];
  parentId: number | null;
  onChanged: () => void;
}) {
  const [name, setName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const children = topics.filter((t) => t.parent_id === parentId);

  // Long-pressing a topic opens a small menu of actions (for now only Delete)
  const openMenu = async (topic: TopicWithTotals) => {
    const choice = await showMenu(topic.name, [{ label: 'Delete', destructive: true }]);
    if (choice !== 0) return;
    try {
      if (await confirmAndDeleteTopic(topic, topics)) onChanged();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    }
  };

  const addTopic = async () => {
    try {
      await api.createTopic(name.trim(), parentId);
      setName('');
      setError(null);
      onChanged();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    }
  };

  return (
    <View style={{ gap: Spacing.two }}>
      <SectionTitle>{parentId === null ? 'Topics' : 'Subtopics'}</SectionTitle>
      {children.map((topic) => (
        <Row
          key={topic.id}
          title={topic.name}
          detail={topic.total_due ? `${topic.total_due} due · ${topic.total_cards}` : String(topic.total_cards)}
          onPress={() => router.push({ pathname: '/topic/[id]', params: { id: String(topic.id) } })}
          onLongPress={() => openMenu(topic)}
        />
      ))}
      <View style={{ flexDirection: 'row', gap: Spacing.two }}>
        <Input
          style={{ flex: 3 }}
          value={name}
          onChangeText={setName}
          placeholder={parentId === null ? 'New topic' : 'New subtopic'}
          onSubmitEditing={addTopic}
        />
        <Button title="Add" onPress={addTopic} disabled={!name.trim()} />
      </View>
      {error ? <Label muted>{error}</Label> : null}
    </View>
  );
}
