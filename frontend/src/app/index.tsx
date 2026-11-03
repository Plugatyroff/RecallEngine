import { router, Stack } from 'expo-router';
import { Pressable, ScrollView, Text } from 'react-native';

import { TopicList } from '@/components/topic-list';
import { Button, ErrorMessage, Loading, Screen } from '@/components/ui';
import { Spacing } from '@/constants/theme';
import { useApi } from '@/hooks/use-api';
import { useTheme } from '@/hooks/use-theme';
import { withTotals } from '@/lib/topics';
import { api } from '@/services/api';

/** The "+" in the header, leading to the screen for adding decks from Anki. */
function AddDecksButton() {
  const colors = useTheme();
  return (
    <Pressable onPress={() => router.push('/import')} hitSlop={12} accessibilityLabel="Add decks from Anki">
      <Text style={{ color: colors.text, fontSize: 28, lineHeight: 30, paddingHorizontal: Spacing.two }}>+</Text>
    </Pressable>
  );
}

/** Main menu: the top-level topics and the review button. */
export default function HomeScreen() {
  const { data, error, loading, reload } = useApi(api.topics);

  if (loading) return <Loading />;
  if (error && !data) return <ErrorMessage message={error} onRetry={reload} />;

  const topics = withTotals(data ?? []);
  const due = topics.reduce((sum, t) => sum + t.due_count, 0);

  return (
    <Screen>
      <Stack.Screen options={{ headerRight: () => <AddDecksButton /> }} />
      <ScrollView contentContainerStyle={{ gap: Spacing.two }}>
        <Button
          primary
          title={due ? `Review ${due} due` : 'Review'}
          subtitle={due ? undefined : 'Nothing due — learn new cards'}
          onPress={() => router.push('/review')}
        />
        <TopicList topics={topics} parentId={null} onChanged={reload} />
      </ScrollView>
    </Screen>
  );
}
