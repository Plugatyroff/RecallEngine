import { router, Stack, useLocalSearchParams } from 'expo-router';
import { useCallback } from 'react';
import { ScrollView, View } from 'react-native';

import { TopicList } from '@/components/topic-list';
import { Button, ErrorMessage, Label, Loading, Row, Screen, SectionTitle } from '@/components/ui';
import { Spacing } from '@/constants/theme';
import { useApi } from '@/hooks/use-api';
import { formatInterval } from '@/lib/format';
import { withTotals } from '@/lib/topics';
import { api } from '@/services/api';

/** One topic: its subtopics and its cards. */
export default function TopicScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const topicId = Number(id);
  const load = useCallback(() => Promise.all([api.topics(), api.cardsInTopic(topicId)]), [topicId]);
  const { data, error, loading, reload } = useApi(load);

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
      </ScrollView>
    </Screen>
  );
}
