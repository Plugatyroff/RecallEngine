import { router, Stack, useLocalSearchParams } from 'expo-router';
import { useCallback, useState } from 'react';
import { ScrollView, View } from 'react-native';

import { TopicList } from '@/components/topic-list';
import { Button, ErrorMessage, Label, Loading, Row, Screen, SectionTitle } from '@/components/ui';
import { Spacing } from '@/constants/theme';
import { useApi } from '@/hooks/use-api';
import { confirm } from '@/lib/confirm';
import { formatInterval } from '@/lib/format';
import { countDescendants, withTotals, type TopicWithTotals } from '@/lib/topics';
import { api, ApiError } from '@/services/api';

/** One topic: its subtopics and its cards. */
export default function TopicScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const topicId = Number(id);
  const load = useCallback(() => Promise.all([api.topics(), api.cardsInTopic(topicId)]), [topicId]);
  const { data, error, loading, reload } = useApi(load);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const deleteTopic = async (topic: TopicWithTotals, subtopics: number) => {
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
    if (!confirmed) return;
    try {
      await api.deleteTopic(topic.id);
      // Return to where the user came from; if this screen was opened directly, go to the main menu
      if (router.canGoBack()) {
        router.back();
      } else {
        router.replace('/');
      }
    } catch (e) {
      setDeleteError(e instanceof ApiError ? e.message : String(e));
    }
  };

  if (loading) return <Loading />;
  if (error && !data) return <ErrorMessage message={error} onRetry={reload} />;

  const [topicList, cards] = data ?? [[], []];
  const topics = withTotals(topicList);
  const topic = topics.find((t) => t.id === topicId);
  const now = new Date();

  return (
    <Screen>
      <Stack.Screen options={{ title: topic?.name ?? '' }} />
      <ScrollView contentContainerStyle={{ gap: Spacing.two }}>
        {topic && topic.total_cards > 0 ? (
          <View style={{ flexDirection: 'row' }}>
            <Button
              primary
              title={topic.total_due ? `Review ${topic.total_due} due` : 'Review'}
              subtitle={topic.total_due ? 'this topic and its subtopics' : 'Nothing due — learn new cards'}
              onPress={() => router.push({ pathname: '/review', params: { topicId: String(topicId) } })}
            />
          </View>
        ) : null}
        <TopicList topics={topics} parentId={topicId} onChanged={reload} />

        <SectionTitle>Cards</SectionTitle>
        {cards.length === 0 ? <Label muted>No cards here yet.</Label> : null}
        {cards.map((card) => (
          <Row
            key={card.id}
            title={card.preview || '(image)'}
            detail={
              card.status === 'new'
                ? 'new'
                : card.due_at && new Date(card.due_at) <= now
                  ? 'due'
                  : card.due_at
                    ? `in ${formatInterval(now, card.due_at)}`
                    : undefined
            }
            onPress={() => router.push({ pathname: '/card/[id]', params: { id: String(card.id) } })}
          />
        ))}
        <View style={{ flexDirection: 'row', marginTop: Spacing.two }}>
          <Button
            title="+ Add card"
            onPress={() => router.push({ pathname: '/add-card', params: { topicId: String(topicId) } })}
          />
        </View>
        {topic ? (
          <View style={{ flexDirection: 'row', marginTop: Spacing.four }}>
            <Button danger title="Delete topic" onPress={() => deleteTopic(topic, countDescendants(topicList, topicId))} />
          </View>
        ) : null}
        {deleteError ? <Label muted>{deleteError}</Label> : null}
      </ScrollView>
    </Screen>
  );
}
